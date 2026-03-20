"""Keells Super Sri Lankan supermarket spider."""

from __future__ import annotations

from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser


class KeellsSpider(BaseSpider):
    """Scrape product listings from Keells Super (Sri Lankan supermarket).

    Keells Super is a Sri Lankan online supermarket. It uses JavaScript rendering
    for product listings.

    Usage:
        python -m scripts.run_spider keells --url "https://www.keellssuper.com/"
        python -m scripts.run_spider keells --url "https://www.keellssuper.com/search?q=rice"
    """

    name = "keells"
    allowed_domains = ["keellssuper.com"]
    use_playwright = True

    playwright_config = {
        "stealth_mode": True,
    }

    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 4,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="div[class*='product'], div[class*='item']",
                wait_for_timeout=3000,
                api_interception_patterns=[
                    "**/api/**",
                    "**/graphql**",
                    "**/*.json",
                ]
            )

    async def parse(self, response):
        """Parse Keells product listings."""
        page = response.meta.get("playwright_page")

        self._record_success(response.url)

        # Try API interception first
        api_data = ApiParser.extract_from_intercepted(response, r"/api")

        if api_data:
            yield from self._parse_from_api(api_data)

        # Also try GraphQL
        graphql_data = ApiParser.parse_graphql_response(response)
        if graphql_data:
            yield from self._parse_from_api(graphql_data)

        # Parse from HTML
        yield from self._parse_from_html(response)

        # Scroll to load more products (if infinite scroll)
        if page:
            initial_count = len(response.css("div[class*='product']"))

            for _ in range(2):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            # Check if more products loaded
            final_count = len(await page.query_selector_all("div[class*='product']"))
            if final_count > initial_count:
                self.logger.info(f"Loaded {final_count - initial_count} more products via scroll")

        # Follow pagination
        next_page = response.css(
            "a.next::attr(href), "
            "a[aria-label='Next']::attr(href), "
            "button[class*='next']:not([disabled])::attr(href), "
            "link[rel='next']::attr(href)"
        ).get()

        if next_page:
            yield self.make_playwright_request(
                response.urljoin(next_page),
                self.parse,
                wait_for_selector="div[class*='product']",
                api_interception_patterns=["**/api/**", "**/graphql**"]
            )

    def _parse_from_api(self, api_data):
        """Extract products from API responses."""
        for item in api_data:
            if not isinstance(item, dict):
                continue

            product_id = item.get("id") or item.get("productId") or item.get("sku")
            name = item.get("name") or item.get("title") or item.get("productName")

            if product_id or name:
                yield {
                    "product_id": product_id,
                    "name": name,
                    "price": self._extract_price(item, "price"),
                    "original_price": self._extract_price(item, "originalPrice"),
                    "currency": item.get("currency", "LKR"),
                    "discount": item.get("discount") or item.get("discountPercentage"),
                    "category": self._extract_category(item),
                    "brand": item.get("brand"),
                    "unit": item.get("unit") or item.get("packSize"),
                    "weight": item.get("weight"),
                    "in_stock": item.get("inStock") or item.get("available", True),
                    "stock_quantity": item.get("stockQuantity") or item.get("quantity"),
                    "image_url": self._extract_image_url(item),
                    "images": item.get("images") or item.get("imageUrls"),
                    "url": self._build_product_url(item),
                    "description": item.get("description"),
                    "rating": item.get("rating") or item.get("averageRating"),
                    "review_count": item.get("reviewCount") or item.get("reviews"),
                    "source": "keells-api",
                }
                self._record_item("product")

    def _parse_from_html(self, response):
        """Parse products from HTML."""
        # Try various product selectors
        product_selectors = [
            "div.product-card",
            "div[class*='product-item']",
            "div[class*='ProductCard']",
            "li[class*='product']",
            "article[class*='product']",
        ]

        products = []
        for selector in product_selectors:
            products = response.css(selector)
            if products:
                self.logger.info(f"Found {len(products)} products using selector: {selector}")
                break

        for product in products:
            name = product.css(
                "h2::text, h3::text, "
                "div[class*='title']::text, "
                "a[class*='title']::text, "
                "span[class*='name']::text"
            ).get()

            if not name:
                continue

            # Extract price
            price = product.css(
                "span[class*='price']:not([class*='original'])::text, "
                "div[class*='price']:not([class*='original'])::text, "
                "span[class*='Price']:not([class*='original'])::text"
            ).get()

            original_price = product.css(
                "span[class*='original-price']::text, "
                "span[class*='was-price']::text, "
                "del::text, "
                "s::text"
            ).get()

            yield {
                "name": name.strip(),
                "price": self._clean_price_string(price),
                "original_price": self._clean_price_string(original_price),
                "currency": "LKR",
                "discount": product.css("span[class*='discount']::text, span[class*='save']::text").get(),
                "category": product.css("span[class*='category']::text, a[class*='category']::text").get(),
                "brand": product.css("span[class*='brand']::text").get(),
                "unit": product.css("span[class*='unit']::text, span[class*='size']::text").get(),
                "in_stock": not bool(product.css("span:contains('Out of Stock'), div[class*='out-of-stock']")),
                "image_url": product.css("img::attr(src), img::attr(data-src)").get(),
                "url": response.urljoin(product.css("a::attr(href)").get()),
                "rating": product.css("span[class*='rating']::text, div[class*='rating']::attr(aria-label)").get(),
                "source": "keells-html",
            }
            self._record_item("product")

    def _extract_price(self, item: dict, price_key: str) -> float | None:
        """Extract and clean price from API data."""
        price = item.get(price_key)
        if price is None:
            # Try alternative keys
            if price_key == "price":
                price = item.get("salePrice") or item.get("sellingPrice") or item.get("currentPrice")

        if isinstance(price, (int, float)):
            return float(price)
        elif isinstance(price, str):
            return self._clean_price_string(price)
        elif isinstance(price, dict):
            # Price might be in a nested object
            return price.get("value") or price.get("amount")
        return None

    def _clean_price_string(self, price_str: str | None) -> float | None:
        """Clean price string to float."""
        if not price_str:
            return None

        import re
        # Remove currency symbols and commas, keep only digits and decimal point
        cleaned = re.sub(r"[^\d.]", "", str(price_str))
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _extract_category(self, item: dict) -> str | None:
        """Extract category from various structures."""
        category = item.get("category") or item.get("categoryName")

        if isinstance(category, dict):
            return category.get("name") or category.get("title")
        elif isinstance(category, list) and category:
            # Get first category or join them
            first_cat = category[0]
            if isinstance(first_cat, dict):
                return first_cat.get("name") or first_cat.get("title")
            return str(first_cat)
        elif isinstance(category, str):
            return category

        return None

    def _extract_image_url(self, item: dict) -> str | None:
        """Extract image URL from various structures."""
        image_keys = ["imageUrl", "image", "thumbnail", "mainImage", "primaryImage"]

        for key in image_keys:
            value = item.get(key)
            if isinstance(value, str):
                return value if value.startswith("http") else f"https://www.keellssuper.com{value}"
            elif isinstance(value, dict):
                url = value.get("url") or value.get("src")
                if url:
                    return url if url.startswith("http") else f"https://www.keellssuper.com{url}"
            elif isinstance(value, list) and value:
                first_img = value[0]
                if isinstance(first_img, str):
                    return first_img if first_img.startswith("http") else f"https://www.keellssuper.com{first_img}"
                elif isinstance(first_img, dict):
                    url = first_img.get("url") or first_img.get("src")
                    if url:
                        return url if url.startswith("http") else f"https://www.keellssuper.com{url}"

        return None

    def _build_product_url(self, item: dict) -> str | None:
        """Build product URL from item data."""
        # Try getting URL directly
        url = item.get("url") or item.get("productUrl") or item.get("link")
        if url:
            return url if url.startswith("http") else f"https://www.keellssuper.com{url}"

        # Try building from slug or ID
        slug = item.get("slug") or item.get("handle")
        product_id = item.get("id") or item.get("productId")

        if slug:
            return f"https://www.keellssuper.com/product/{slug}"
        elif product_id:
            return f"https://www.keellssuper.com/product/{product_id}"

        return None
