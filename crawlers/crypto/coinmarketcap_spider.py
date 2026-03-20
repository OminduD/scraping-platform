"""CoinMarketCap cryptocurrency data spider."""

from __future__ import annotations

from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser


class CoinMarketCapSpider(BaseSpider):
    """Scrape cryptocurrency data from CoinMarketCap.

    CoinMarketCap loads data via JSON APIs. This spider intercepts those APIs
    to get clean cryptocurrency data including prices, market cap, volume, etc.

    Usage:
        python -m scripts.run_spider coinmarketcap --url "https://coinmarketcap.com/"
        python -m scripts.run_spider coinmarketcap --url "https://coinmarketcap.com/currencies/bitcoin/"
    """

    name = "coinmarketcap"
    allowed_domains = ["coinmarketcap.com"]
    use_playwright = True

    playwright_config = {
        "stealth_mode": True,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="table[class*='cmc-table'], div[class*='price']",
                wait_for_timeout=3000,
                api_interception_patterns=[
                    "**/v1/cryptocurrency/listings/**",
                    "**/data-api/v3/**",
                    "**/v1/cryptocurrency/quotes/**",
                    "**/api/v1/**",
                ]
            )

    def parse(self, response):
        self._record_success(response.url)

        # Try API interception first
        api_data = self._extract_crypto_from_apis(response)

        if api_data:
            for crypto in api_data:
                yield crypto
        else:
            # Fallback to HTML parsing
            yield from self._parse_from_html(response)

    def _extract_crypto_from_apis(self, response):
        """Extract cryptocurrency data from intercepted APIs."""
        results = []

        # Try different API patterns
        api_patterns = [
            (r"/cryptocurrency/listings", "data"),
            (r"/cryptocurrency/quotes", "data"),
            (r"/data-api/v3", None),
            (r"/api/v1", "data"),
        ]

        for pattern, key_path in api_patterns:
            data = ApiParser.extract_from_intercepted(response, pattern, key_path=key_path)

            if data:
                for item in data if isinstance(data, list) else [data]:
                    crypto = self._parse_crypto_item(item)
                    if crypto:
                        results.append(crypto)
                        self._record_item("crypto")

        return results

    def _parse_crypto_item(self, item: dict) -> dict | None:
        """Parse a single cryptocurrency item from API response."""
        if not isinstance(item, dict):
            return None

        # Handle different API response structures
        crypto_id = item.get("id") or item.get("cryptoId")
        symbol = item.get("symbol")
        name = item.get("name")

        if not (symbol or name):
            return None

        # Extract quote data (usually in USD)
        quote = item.get("quote", {})
        usd_quote = quote.get("USD", {}) if isinstance(quote, dict) else {}

        # Handle prices that might be at root level or in quote
        price = (
            item.get("price") or
            usd_quote.get("price") or
            item.get("quotes", {}).get("USD", {}).get("price")
        )

        return {
            "rank": item.get("cmc_rank") or item.get("rank"),
            "name": name,
            "symbol": symbol,
            "slug": item.get("slug"),
            "price": price,
            "market_cap": usd_quote.get("market_cap") or item.get("market_cap"),
            "volume_24h": usd_quote.get("volume_24h") or item.get("volume_24h"),
            "volume_change_24h": usd_quote.get("volume_change_24h"),
            "percent_change_1h": usd_quote.get("percent_change_1h"),
            "percent_change_24h": usd_quote.get("percent_change_24h") or item.get("percent_change_24h"),
            "percent_change_7d": usd_quote.get("percent_change_7d"),
            "percent_change_30d": usd_quote.get("percent_change_30d"),
            "circulating_supply": item.get("circulating_supply"),
            "total_supply": item.get("total_supply"),
            "max_supply": item.get("max_supply"),
            "url": f"https://coinmarketcap.com/currencies/{item.get('slug')}/" if item.get('slug') else None,
            "source": "coinmarketcap-api",
        }

    def _parse_from_html(self, response):
        """HTML parsing fallback for when API interception fails."""
        # Try table rows first (main listing page)
        rows = response.css("table tbody tr, div[class*='table'] div[class*='row']")

        for row in rows:
            name = row.css("p[class*='name']::text, a[class*='name']::text, td:nth-child(3)::text").get()
            symbol = row.css("p[class*='symbol']::text, span[class*='symbol']::text, td:nth-child(3) span::text").get()

            if name or symbol:
                yield {
                    "rank": row.css("div[class*='rank']::text, td:nth-child(2)::text").get(),
                    "name": name,
                    "symbol": symbol,
                    "price": row.css("span[class*='price']::text, td:nth-child(4)::text").get(),
                    "percent_change_24h": row.css("span[class*='change']::text, td:nth-child(5)::text").get(),
                    "market_cap": row.css("span[class*='market-cap']::text, td:nth-child(7)::text").get(),
                    "volume_24h": row.css("span[class*='volume']::text, td:nth-child(8)::text").get(),
                    "url": response.urljoin(row.css("a::attr(href)").get()),
                    "source": "coinmarketcap-html",
                }
                self._record_item("crypto")

        # Try embedded JSON data (Next.js)
        json_data = ApiParser.find_json_in_html(response)
        for data in json_data:
            if data.get("source") == "next-data":
                # Extract crypto data from Next.js data
                props_data = data.get("data", {}).get("props", {}).get("pageProps", {})
                cryptos = (
                    props_data.get("initialData") or
                    props_data.get("cryptoCurrencyList") or
                    []
                )

                for item in cryptos if isinstance(cryptos, list) else [cryptos]:
                    if isinstance(item, dict):
                        crypto = self._parse_crypto_item(item)
                        if crypto:
                            yield crypto

    async def _is_blocked(self, page, response) -> bool:
        """Check if we're blocked by anti-bot systems."""
        if not page:
            return False

        # Check for CloudFlare
        cf_challenge = await page.query_selector("div#cf-wrapper")
        if cf_challenge:
            return True

        # Check for CAPTCHA
        captcha = await page.query_selector("div[class*='captcha']")
        if captcha:
            return True

        return False
