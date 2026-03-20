"""AliExpress product spider."""

from __future__ import annotations

from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser


class AliExpressSpider(BaseSpider):
    """Scrape AliExpress product listings.

    AliExpress uses JavaScript rendering and has CloudFlare protection.
    This spider uses Playwright with stealth mode and API interception.

    Usage:
        python -m scripts.run_spider aliexpress --url "https://www.aliexpress.com/category/...?SearchText=laptop"
    """

    name = "aliexpress"
    allowed_domains = ["aliexpress.com", "aliexpress.us"]
    use_playwright = True

    playwright_config = {
        "stealth_mode": True,
        "wait_for_timeout": 5000,  # AliExpress needs time to load
    }

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 2,  # Lower concurrency to avoid detection
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    async def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="div[class*='product'], div[class*='item']",
                wait_for_timeout=5000,
                api_interception_patterns=[
                    "**/api/recommend/**",
                    "**/api/search/**",
                    "**/api/products/**",
                    "**/mtop.**",  # AliExpress mobile API
                ],
            )

    async def parse(self, response):
        """Parse AliExpress product listings."""
        page = response.meta.get("playwright_page")

        # Check for CloudFlare or bot detection
        if await self._is_blocked(page, response):
            self.logger.warning(f"Bot detected or blocked: {response.url}")
            return

        self._record_success(response.url)

        # Try API interception first
        api_data = ApiParser.extract_from_intercepted(
            response,
            r"/(api|mtop)",
            key_path=None  # Structure varies
        )

        if api_data:
            yield from self._parse_from_api(api_data)
        else:
            # Fallback to HTML parsing
            yield from self._parse_from_html(response)

        # Scroll to load more products (lazy loading)
        if page:
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            # Re-parse after scroll
            updated_response = await page.content()
            # Note: Would need to create new response object here for full implementation

    def _parse_from_api(self, api_data):
        """Extract products from API responses."""
        for item in api_data:
            if not isinstance(item, dict):
                continue

            # AliExpress API structure can vary, handle multiple patterns
            product_id = (
                item.get("productId") or
                item.get("itemId") or
                item.get("id")
            )

            if product_id or item.get("title") or item.get("productTitle"):
                yield {
                    "product_id": product_id,
                    "title": item.get("title") or item.get("productTitle") or item.get("subject"),
                    "price": self._extract_price(item),
                    "original_price": item.get("originalPrice") or item.get("salePrice", {}).get("max"),
                    "currency": item.get("currency", "USD"),
                    "rating": item.get("averageStar") or item.get("rating"),
                    "orders": item.get("tradeCount") or item.get("orders"),
                    "image_url": self._extract_image(item),
                    "seller": item.get("storeName") or item.get("shopName"),
                    "url": self._build_product_url(item),
                    "shipping_info": item.get("shipping") or item.get("logisticsDesc"),
                    "source": "aliexpress-api",
                }
                self._record_item("product")

    def _parse_from_html(self, response):
        """HTML parsing fallback."""
        # AliExpress has multiple page layouts, try common selectors
        selectors = [
            "div[class*='product-item']",
            "div[class*='item-card']",
            "a[class*='product']",
            "div.list-item",
        ]

        products = []
        for selector in selectors:
            products = response.css(selector)
            if products:
                break

        for product in products:
            title = product.css("h1::text, h3::text, div[class*='title']::text, a::attr(title)").get()

            if title:
                yield {
                    "title": title.strip(),
                    "price": product.css(
                        "span[class*='price']::text, "
                        "div[class*='price']::text, "
                        "strong[class*='price']::text"
                    ).get(),
                    "rating": product.css("span[class*='rating']::text, span[class*='star']::text").get(),
                    "orders": product.css("span[class*='trade']::text, span[class*='order']::text").get(),
                    "image_url": product.css("img::attr(src), img::attr(data-src)").get(),
                    "url": response.urljoin(product.css("a::attr(href)").get()),
                    "source": "aliexpress-html",
                }
                self._record_item("product")

    async def _is_blocked(self, page, response) -> bool:
        """Check if we're blocked by anti-bot systems."""
        if not page:
            return False

        # Check for CloudFlare
        cf_challenge = await page.query_selector("div#cf-wrapper, form#challenge-form")
        if cf_challenge:
            return True

        # Check for CAPTCHA
        captcha = await page.query_selector("div[class*='captcha'], div[class*='verify']")
        if captcha:
            return True

        # Check response text for common block messages
        text = response.text.lower()
        if any(phrase in text for phrase in ["access denied", "blocked", "captcha"]):
            return True

        return False

    def _extract_price(self, item: dict) -> float | None:
        """Extract price from various API structures."""
        price_keys = [
            "price", "minPrice", "salePrice", "targetPrice",
            ["prices", "salePrice", "min"],
            ["priceInfo", "price"],
        ]

        for key in price_keys:
            if isinstance(key, list):
                value = item
                for k in key:
                    value = value.get(k, {}) if isinstance(value, dict) else None
                    if value is None:
                        break
                if value:
                    return self._clean_price(value)
            else:
                value = item.get(key)
                if value:
                    return self._clean_price(value)
        return None

    def _clean_price(self, value) -> float | None:
        """Clean price value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove currency symbols and convert
            import re
            cleaned = re.sub(r"[^\d.]", "", value)
            try:
                return float(cleaned)
            except ValueError:
                pass
        return None

    def _extract_image(self, item: dict) -> str | None:
        """Extract image URL from various structures."""
        image_keys = ["imageUrl", "imgUrl", "image", "productImage", "thumbnail"]
        for key in image_keys:
            if key in item:
                url = item[key]
                if isinstance(url, str):
                    return url if url.startswith("http") else f"https:{url}"
        return None

    def _build_product_url(self, item: dict) -> str | None:
        """Build product URL from item data."""
        product_id = item.get("productId") or item.get("itemId")
        if product_id:
            return f"https://www.aliexpress.com/item/{product_id}.html"

        # Try getting URL directly
        url = item.get("url") or item.get("productUrl")
        if url:
            return url if url.startswith("http") else f"https://www.aliexpress.com{url}"

        return None
