"""Product listing spider — scrapes product data from an example e-commerce site.

This is a demonstration spider.  Replace `start_urls` and selector logic with
a real target to use in production.
"""

from __future__ import annotations

from typing import Any, Generator

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

    def parse(self, response: scrapy.http.Response, **kwargs) -> Generator:
        self._record_success(response.url)

        for product in response.css("article.product_pod"):
            item = {
                "title": product.css("h3 a::attr(title)").get("").strip(),
                "price": product.css("p.price_color::text").get("").strip(),
                "url": response.urljoin(product.css("h3 a::attr(href)").get("")),
                "availability": product.css("p.availability::text").re_first(r"\S+"),
                "rating": product.css("p.star-rating::attr(class)").re_first(r"star-rating (\w+)"),
                "source": "books.toscrape.com",
            }
            self._record_item("product")
            logger.debug("item.scraped", spider=self.name, title=item["title"])
            yield item

        # Follow pagination
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            self._record_start(response.urljoin(next_page))
            yield response.follow(next_page, callback=self.parse, errback=self._on_error)
