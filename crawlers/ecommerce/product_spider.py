"""Product listing spider — scrapes product data from e-commerce sites.

Supports:
- books.toscrape.com  (default demo site)
- WooCommerce stores  (detected automatically by page structure)

Pass ``--url`` to *run_spider* to crawl any supported store.
"""

from __future__ import annotations

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
        "FEEDS": {
            "data/processed/products.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
            },
        },
    }

    def __init__(
        self,
        *args: Any,
        start_urls: list[str] | None = None,
        download_images: bool | str = False,
        **kwargs: Any,
    ) -> None:
        if isinstance(download_images, str):
            self.download_images = download_images.lower() in {"1", "true", "yes", "on"}
        else:
            self.download_images = bool(download_images)

        if start_urls:
            self.start_urls = start_urls
            # Derive allowed_domains from the provided URLs
            self.allowed_domains = list(
                {urlparse(u).hostname for u in start_urls if urlparse(u).hostname}
            )
        super().__init__(*args, **kwargs)

    def parse(self, response: scrapy.http.Response, **kwargs) -> Generator:
        self._record_success(response.url)

        # Detect site type and delegate to the right parser
        if response.css("ul.products li.product"):
            yield from self._parse_woocommerce(response)
        else:
            yield from self._parse_books_toscrape(response)

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
            # Prefer sale (ins) price, fall back to regular price
            price = (
                product.css(".price ins .woocommerce-Price-amount::text").get("")
                or product.css(".price .woocommerce-Price-amount::text").get("")
                or product.css(".price ins::text").get("")
                or product.css(".price::text").get("")
            ).strip()
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
