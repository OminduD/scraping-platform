"""Yelp business listings spider."""

from __future__ import annotations

from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser


class YelpSpider(BaseSpider):
    """Scrape Yelp business listings using GraphQL API interception.

    Yelp loads data via GraphQL APIs. This spider intercepts those APIs
    for clean, structured data extraction.

    Usage:
        python -m scripts.run_spider yelp --url "https://www.yelp.com/search?find_desc=pizza&find_loc=NYC"
    """

    name = "yelp"
    allowed_domains = ["yelp.com"]
    use_playwright = True

    playwright_config = {
        "stealth_mode": True,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="div[data-testid='serp-ia-card']",
                wait_for_timeout=3000,
                api_interception_patterns=[
                    "**/gql**",           # GraphQL API
                    "**/api/v3/**",       # REST API
                    "**/biz/**/*.json",   # Business details
                ]
            )

    def parse(self, response):
        self._record_success(response.url)

        # Try API-first approach (GraphQL)
        graphql_data = ApiParser.parse_graphql_response(response)

        if graphql_data:
            yield from self._parse_from_api(graphql_data)
        else:
            # Fallback to HTML parsing
            yield from self._parse_from_html(response)

    def _parse_from_api(self, graphql_data):
        """Extract business data from GraphQL API responses."""
        for item in graphql_data:
            if not isinstance(item, dict):
                continue

            # Extract business info from GraphQL structure
            business_id = item.get("bizId") or item.get("id") or item.get("alias")

            if business_id or item.get("name"):
                business = {
                    "name": item.get("name"),
                    "alias": item.get("alias"),
                    "rating": item.get("rating"),
                    "review_count": item.get("reviewCount") or item.get("review_count"),
                    "price_range": item.get("priceRange") or item.get("price"),
                    "phone": item.get("phone"),
                    "address": self._extract_address(item),
                    "categories": self._extract_categories(item),
                    "url": f"https://www.yelp.com/biz/{item.get('alias', business_id)}" if item.get('alias') or business_id else None,
                    "is_closed": item.get("isClosed"),
                    "source": "yelp-graphql",
                }

                yield business
                self._record_item("business")

    def _parse_from_html(self, response):
        """Fallback HTML parsing for when API interception fails."""
        for card in response.css("div[data-testid='serp-ia-card'], li[class*='businessCard']"):
            name = card.css("h3 a::text, h2 a::text, a[name*='business'] span::text").get()

            if name:
                yield {
                    "name": name.strip(),
                    "rating": card.css("div[aria-label*='star']::attr(aria-label), span[class*='rating']::text").get(),
                    "review_count": card.css("span[class*='reviewCount']::text, span:contains('reviews')::text").get(),
                    "price_range": card.css("span[class*='priceRange']::text, span:contains('$')::text").get(),
                    "category": card.css("span[class*='category']::text, a[class*='category']::text").get(),
                    "url": response.urljoin(card.css("a::attr(href)").get()),
                    "location": card.css("span[class*='location']::text, p[class*='address']::text").get(),
                    "source": "yelp-html",
                }
                self._record_item("business")

        # Follow pagination
        next_page = response.css("a[aria-label='Next'], link[rel='next']::attr(href)").get()
        if next_page:
            yield self.make_playwright_request(
                response.urljoin(next_page),
                self.parse,
                wait_for_selector="div[data-testid='serp-ia-card']",
                wait_for_timeout=2000,
                api_interception_patterns=["**/gql**", "**/api/v3/**"]
            )

    def _extract_address(self, item: dict) -> str | None:
        """Extract address from various GraphQL structures."""
        location = item.get("location", {})
        if isinstance(location, dict):
            parts = [
                location.get("address1"),
                location.get("city"),
                location.get("state"),
                location.get("zip_code"),
            ]
            return ", ".join(filter(None, parts)) or None
        return None

    def _extract_categories(self, item: dict) -> list[str]:
        """Extract categories from GraphQL data."""
        categories = item.get("categories", [])
        if isinstance(categories, list):
            return [
                cat.get("title") or cat.get("alias")
                for cat in categories
                if isinstance(cat, dict) and (cat.get("title") or cat.get("alias"))
            ]
        return []
