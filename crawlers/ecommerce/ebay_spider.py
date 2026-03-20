"""eBay product spider."""

from __future__ import annotations

import json

from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser


class EbaySpider(BaseSpider):
    """Scrape eBay product listings.

    eBay uses JavaScript rendering and has bot detection.
    This spider uses Playwright with stealth mode and can extract from APIs or HTML.

    Usage:
        python -m scripts.run_spider ebay --url "https://www.ebay.com/sch/i.html?_nkw=laptop"
    """

    name = "ebay"
    allowed_domains = ["ebay.com"]
    use_playwright = True

    playwright_config = {
        "stealth_mode": True,
    }

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="li[class*='s-item'], div.srp-results",
                wait_for_timeout=3000,
                api_interception_patterns=[
                    "**/api/**",
                    "**/sch/**/*.json",
                    "**/roverimp/**",
                ]
            )

    def parse(self, response):
        self._record_success(response.url)

        # Try embedded JSON first (eBay often embeds data in scripts)
        json_data = ApiParser.find_json_in_html(response)
        if json_data:
            yield from self._parse_from_json(json_data, response)

        # Parse from HTML
        yield from self._parse_from_html(response)

        # Follow pagination
        next_page = response.css(
            "a.pagination__next::attr(href), "
            "a[type='next']::attr(href), "
            "nav.pagination a:contains('Next')::attr(href)"
        ).get()

        if next_page:
            yield self.make_playwright_request(
                response.urljoin(next_page),
                self.parse,
                wait_for_selector="li[class*='s-item']",
                wait_for_timeout=2000,
                api_interception_patterns=["**/api/**"]
            )

    def _parse_from_json(self, json_data_list, response):
        """Extract products from embedded JSON data."""
        for data_wrapper in json_data_list:
            data = data_wrapper.get("data", {})

            # eBay embeds product data in various JSON structures
            items = (
                data.get("items") or
                data.get("itemSummaries") or
                data.get("products") or
                []
            )

            for item in items if isinstance(items, list) else [items]:
                if not isinstance(item, dict):
                    continue

                product = self._parse_product_item(item)
                if product:
                    product["source"] = "ebay-json"
                    yield product
                    self._record_item("product")

    def _parse_from_html(self, response):
        """Parse products from HTML."""
        # eBay search results
        items = response.css(
            "li.s-item, "
            "div.s-item__wrapper, "
            "div[class*='srp-river-results'] > ul > li"
        )

        for item in items:
            # Skip header/empty items
            title = item.css(
                "h3.s-item__title::text, "
                "div.s-item__title > span::text, "
                "a.s-item__link span[role='heading']::text"
            ).get()

            if not title or title.lower() in ["shop on ebay", ""]:
                continue

            yield {
                "title": title.strip(),
                "price": item.css(
                    "span.s-item__price::text, "
                    "span[class*='price']::text"
                ).get(),
                "currency": "USD",  # Extract from price string if needed
                "condition": item.css("span.SECONDARY_INFO::text, span[class*='condition']::text").get(),
                "shipping": item.css("span.s-item__shipping::text, span[class*='shipping']::text").get(),
                "location": item.css("span.s-item__location::text, span[class*='location']::text").get(),
                "seller_info": item.css("span.s-item__seller-info-text::text").get(),
                "image_url": item.css("img.s-item__image-img::attr(src), div.s-item__image img::attr(src)").get(),
                "url": item.css("a.s-item__link::attr(href)").get(),
                "item_id": self._extract_item_id(item),
                "bid_count": item.css("span[class*='bids']::text").get(),
                "time_left": item.css("span[class*='time-left']::text").get(),
                "buy_it_now": bool(item.css("span:contains('Buy It Now')")),
                "source": "ebay-html",
            }
            self._record_item("product")

    def _parse_product_item(self, item: dict) -> dict | None:
        """Parse a product item from JSON structure."""
        item_id = item.get("itemId") or item.get("legacyItemId")
        title = item.get("title")

        if not item_id and not title:
            return None

        # Extract price from various structures
        price_info = item.get("price", {}) or item.get("currentPrice", {})
        if isinstance(price_info, dict):
            price = price_info.get("value") or price_info.get("price")
            currency = price_info.get("currency", "USD")
        else:
            price = price_info
            currency = "USD"

        # Extract shipping info
        shipping_info = item.get("shippingOptions", [{}])[0] if item.get("shippingOptions") else {}

        return {
            "item_id": item_id,
            "title": title,
            "price": price,
            "currency": currency,
            "condition": item.get("condition"),
            "seller": item.get("seller", {}).get("username") if isinstance(item.get("seller"), dict) else item.get("seller"),
            "seller_feedback": item.get("seller", {}).get("feedbackPercentage") if isinstance(item.get("seller"), dict) else None,
            "location": item.get("itemLocation", {}).get("city") if isinstance(item.get("itemLocation"), dict) else item.get("location"),
            "shipping": shipping_info.get("shippingCost") if isinstance(shipping_info, dict) else None,
            "image_url": self._extract_image_url(item),
            "url": self._build_ebay_url(item),
            "buy_it_now": item.get("buyingOptions", {}).get("buyItNow") if isinstance(item.get("buyingOptions"), dict) else None,
            "auction": item.get("buyingOptions", {}).get("auction") if isinstance(item.get("buyingOptions"), dict) else None,
        }

    def _extract_image_url(self, item: dict) -> str | None:
        """Extract image URL from item."""
        image = item.get("image") or item.get("thumbnailImages", [{}])[0]
        if isinstance(image, dict):
            return image.get("imageUrl") or image.get("url")
        elif isinstance(image, str):
            return image
        return None

    def _build_ebay_url(self, item: dict) -> str | None:
        """Build product URL from item data."""
        item_id = item.get("itemId") or item.get("legacyItemId")
        if item_id:
            return f"https://www.ebay.com/itm/{item_id}"

        url = item.get("itemWebUrl") or item.get("url")
        return url if url else None

    def _extract_item_id(self, selector) -> str | None:
        """Extract eBay item ID from HTML."""
        # Try to extract from data attributes or URL
        item_id = selector.css("::attr(data-itemid), ::attr(data-item-id)").get()
        if item_id:
            return item_id

        # Try from URL
        url = selector.css("a.s-item__link::attr(href)").get() or ""
        import re
        match = re.search(r"/itm/(\d+)", url)
        return match.group(1) if match else None
