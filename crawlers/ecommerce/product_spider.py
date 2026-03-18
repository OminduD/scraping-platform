"""Product listing spider — scrapes product data from e-commerce sites.

Supports:
- books.toscrape.com  (default demo site)
- WooCommerce stores  (detected automatically by page structure)
- Generic sites       (extracts from JSON-LD, Open Graph, or common HTML patterns)

Pass ``--url`` to *run_spider* to crawl any supported store.
"""

from __future__ import annotations

import json
import re
from typing import Any, Generator
from urllib.parse import urlparse

import scrapy
import structlog

from crawlers.base import BaseSpider

logger = structlog.get_logger(__name__)


class ProductSpider(BaseSpider):
    """Crawl product listing pages and yield structured product items."""

    name = "products"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/catalogue/page-1.html"]

    custom_settings: dict[str, Any] = {
        "DOWNLOAD_DELAY": 1.5,
    }

    # Keep sitemap mode focused on product-related pages to avoid crawling the whole site.
    sitemap_filter_patterns: list[str] = [
        r"/product(?:/|$)",
        r"/products?(?:/|$)",
        r"/product-category(?:/|$)",
        r"/shop(?:/|$)",
        r"/catalog(?:/|$)",
    ]

    def __init__(
        self,
        *args: Any,
        start_urls: list[str] | None = None,
        sitemap_urls: list[str] | None = None,
        sitemap_filter_patterns: list[str] | str | None = None,
        download_images: bool | str = False,
        **kwargs: Any,
    ) -> None:
        if isinstance(download_images, str):
            self.download_images = download_images.lower() in {"1", "true", "yes", "on"}
        else:
            self.download_images = bool(download_images)

        # Derive allowed_domains from provided URLs
        urls_for_domains = start_urls or sitemap_urls or []
        if urls_for_domains:
            self.allowed_domains = list(
                {urlparse(u).hostname for u in urls_for_domains if urlparse(u).hostname}
            )

        if start_urls:
            self.start_urls = start_urls

        if sitemap_filter_patterns:
            if isinstance(sitemap_filter_patterns, str):
                self.sitemap_filter_patterns = [sitemap_filter_patterns]
            else:
                self.sitemap_filter_patterns = list(sitemap_filter_patterns)

        super().__init__(*args, sitemap_urls=sitemap_urls, **kwargs)

    def parse(self, response: scrapy.http.Response, **kwargs) -> Generator:
        self._record_success(response.url)

        # Detect site type and delegate to the right parser
        if response.css("article.product_pod"):
            yield from self._parse_books_toscrape(response)
        elif self._is_product_detail_page(response):
            # Product pages can still contain related-products grids; parse the page itself first.
            yield from self._parse_generic(response)
        elif response.css("ul.products li.product"):
            yield from self._parse_woocommerce(response)
        else:
            yield from self._parse_generic(response)

    # ── books.toscrape.com ───────────────────────────────────────────

    def _parse_books_toscrape(self, response: scrapy.http.Response) -> Generator:
        for product in response.css("article.product_pod"):
            image_url = response.urljoin(
                product.css("div.image_container img::attr(src)").get("")
            )
            item = {
                "title": product.css("h3 a::attr(title)").get("").strip(),
                "price": product.css("p.price_color::text").get("").strip(),
                "url": response.urljoin(product.css("h3 a::attr(href)").get("")),
                "image_url": image_url,
                "availability": product.css("p.availability::text").re_first(r"\S+"),
                "rating": product.css("p.star-rating::attr(class)").re_first(r"star-rating (\w+)"),
                "source": "books.toscrape.com",
            }
            if self.download_images and image_url:
                item["image_urls"] = [image_url]
            self._record_item("product")
            logger.debug("item.scraped", spider=self.name, title=item["title"])
            yield item

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            self._record_start(response.urljoin(next_page))
            yield response.follow(next_page, callback=self.parse, errback=self._on_error)

    # ── WooCommerce stores ───────────────────────────────────────────

    def _parse_woocommerce(self, response: scrapy.http.Response) -> Generator:
        domain = urlparse(response.url).hostname or "unknown"

        for product in response.css("ul.products li.product"):
            link = product.css("a.woocommerce-LoopProduct-link, a[href*='/product/']")
            title = (
                product.css("h2.woocommerce-loop-product__title::text").get("")
                or product.css("h2::text").get("")
            ).strip()
            # WooCommerce prices are often nested in bdi/span nodes.
            price = self._extract_woocommerce_price(product)
            product_url = link.attrib.get("href", "") if link else ""
            image_url = (
                product.css("img::attr(src)").get("")
                or product.css("img::attr(data-src)").get("")
            )

            item = {
                "title": title,
                "price": price,
                "url": response.urljoin(product_url),
                "image_url": image_url,
                "source": domain,
            }
            if self.download_images and image_url:
                item["image_urls"] = [image_url]
            self._record_item("product")
            logger.debug("item.scraped", spider=self.name, title=item["title"])
            yield item

        # WooCommerce pagination
        next_page = response.css("a.next.page-numbers::attr(href)").get()
        if next_page:
            self._record_start(response.urljoin(next_page))
            yield response.follow(next_page, callback=self.parse, errback=self._on_error)

    def _is_product_detail_page(self, response: scrapy.http.Response) -> bool:
        """Detect product detail pages that may also contain related product grids."""
        path = urlparse(response.url).path.lower()
        if "/product/" in path:
            return True

        return bool(
            response.css(
                "body.single-product, div.product.type-product, "
                "form.cart, [itemtype*='schema.org/Product']"
            )
        )

    def _extract_woocommerce_price(self, product: scrapy.Selector) -> str:
        """Extract human-readable price text from WooCommerce list cards."""
        price_texts = [
            t.strip()
            for t in product.css(".price *::text, .price::text").getall()
            if t and t.strip()
        ]
        if price_texts:
            return " ".join(price_texts)

        return (
            product.css(
                ".price::attr(data-price), "
                ".price [itemprop='price']::attr(content), "
                "[itemprop='price']::attr(content)"
            ).get("")
            or ""
        ).strip()

    # ── Generic parser (JSON-LD, Open Graph, HTML patterns) ───────────

    def _parse_generic(self, response: scrapy.http.Response) -> Generator:
        domain = urlparse(response.url).hostname or "unknown"

        # Try JSON-LD first (most reliable)
        items_found = False
        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
                products = self._extract_jsonld_products(data)
                for product in products:
                    product["source"] = domain
                    product["url"] = product.get("url") or response.url
                    if self.download_images and product.get("image_url"):
                        product["image_urls"] = [product["image_url"]]
                    self._record_item("product")
                    logger.debug("item.scraped", spider=self.name, title=product.get("title", ""))
                    yield product
                    items_found = True
            except json.JSONDecodeError:
                continue

        if items_found:
            return

        # Fallback: Try Open Graph meta tags (single product pages)
        og_title = response.css('meta[property="og:title"]::attr(content)').get()
        og_price = (
            response.css('meta[property="product:price:amount"]::attr(content)').get()
            or response.css('meta[property="og:price:amount"]::attr(content)').get()
        )
        og_image = response.css('meta[property="og:image"]::attr(content)').get()

        if og_title:
            item = {
                "title": og_title.strip(),
                "price": og_price or self._extract_price_from_page(response),
                "url": response.url,
                "image_url": og_image or "",
                "source": domain,
            }
            if self.download_images and item.get("image_url"):
                item["image_urls"] = [item["image_url"]]
            self._record_item("product")
            logger.debug("item.scraped", spider=self.name, title=item["title"])
            yield item
            return

        # Last resort: Extract from common HTML patterns
        title = (
            response.css("h1.product-title::text").get()
            or response.css("h1.product_title::text").get()
            or response.css("h1::text").get()
            or response.css("title::text").get()
            or ""
        ).strip()

        if title:
            item = {
                "title": title,
                "price": self._extract_price_from_page(response),
                "url": response.url,
                "image_url": response.css('img.product-image::attr(src), img[id*="product"]::attr(src), .product img::attr(src)').get() or "",
                "source": domain,
            }
            if self.download_images and item.get("image_url"):
                item["image_urls"] = [item["image_url"]]
            self._record_item("product")
            logger.debug("item.scraped", spider=self.name, title=item["title"])
            yield item

    def _extract_jsonld_products(self, data: Any) -> list[dict]:
        """Extract product data from JSON-LD structured data."""
        products = []

        if isinstance(data, list):
            for item in data:
                products.extend(self._extract_jsonld_products(item))
        elif isinstance(data, dict):
            schema_type = data.get("@type", "")
            if schema_type == "Product" or "Product" in str(schema_type):
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price = offers.get("price") or offers.get("lowPrice") or ""
                products.append({
                    "title": data.get("name", "").strip(),
                    "price": str(price),
                    "url": data.get("url", ""),
                    "image_url": data.get("image", [""])[0] if isinstance(data.get("image"), list) else data.get("image", ""),
                    "description": data.get("description", ""),
                })
            # Check for @graph containing products
            if "@graph" in data:
                products.extend(self._extract_jsonld_products(data["@graph"]))

        return products

    def _extract_price_from_page(self, response: scrapy.http.Response) -> str:
        """Try to find a price on the page using common patterns."""
        # Common price selectors (text can be split across nested nodes).
        price_text = " ".join(
            t.strip()
            for t in response.css(
                '.price *::text, .price::text, .product-price *::text, '
                '.product-price::text, [class*="price"]::text'
            ).getall()
            if t and t.strip()
        )
        fallback = (
            response.css(
                'meta[property="product:price:amount"]::attr(content), '
                'meta[property="og:price:amount"]::attr(content), '
                '[itemprop="price"]::attr(content), '
                '[class*="price"]::attr(data-price)'
            ).get("")
            or ""
        ).strip()
        price = price_text or fallback

        # Clean up price - extract first numeric token.
        if price:
            match = re.search(r'[\d,.]+', price)
            if match:
                return match.group(0)
        return price.strip()
