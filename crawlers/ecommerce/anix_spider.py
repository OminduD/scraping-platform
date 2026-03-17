"""Anix.lk product spider — uses sitemap-based URL discovery."""

from __future__ import annotations

from typing import Any, Generator
from urllib.parse import urlparse

import scrapy
import structlog

from crawlers.base import BaseSpider

logger = structlog.get_logger(__name__)


class AnixSpider(BaseSpider):
    """Crawl anix.lk using its sitemap and extract product data."""

    name = "anix"

    sitemap_urls = ["https://anix.lk/sitemap.xml"]
    sitemap_filter_patterns = [r"/product/"]  # only crawl product pages

    custom_settings: dict[str, Any] = {
        "DOWNLOAD_DELAY": 1.5,
        "FEEDS": {
            "data/processed/anix_products.csv": {
                "format": "csv",
                "encoding": "utf-8",
                "overwrite": True,
            },
        },
    }

    def parse(self, response: scrapy.http.Response, **kwargs) -> Generator:
        self._record_success(response.url)
        domain = urlparse(response.url).hostname or "anix.lk"

        title = response.css("h1::text, title::text").get(default="").strip()

        # WooCommerce price selectors (sale price first, then regular)
        price = (
            response.css("p.price ins bdi::text").get("")
            or response.css("p.price bdi::text").get("")
            or "".join(response.css(".price ::text").getall()).strip()
        ).strip()

        if title or price:
            self._record_item("product")
            yield {
                "title": title,
                "price": price,
                "url": response.url,
                "source": domain,
            }
