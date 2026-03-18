"""Transform pipeline — clean, normalize, and deduplicate scraped items.

Runs at priority 200, after the HTML extraction stage.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from scrapy.exceptions import DropItem

logger = structlog.get_logger(__name__)

# Track seen URLs within a single crawl run to drop intra-run duplicates.
_seen_urls: set[str] = set()


class TransformPipeline:
    """Clean field values and drop duplicate items."""

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self, spider) -> None:
        _seen_urls.clear()

    def process_item(self, item: dict[str, Any], spider) -> dict[str, Any]:
        url = item.get("url", "")

        # ── Deduplication ────────────────────────────────────────────
        if url in _seen_urls:
            raise DropItem(f"Duplicate URL: {url}")
        _seen_urls.add(url)

        # ── Normalize text fields ────────────────────────────────────
        for field in ("title", "company", "location", "description"):
            value = item.get(field)
            if isinstance(value, str):
                item[field] = value.strip()

        # ── Parse price strings into float ───────────────────────────
        raw_price = item.get("price")
        if isinstance(raw_price, str):
            item["price"] = _parse_price(raw_price)

        # ── Normalize source to lowercase ────────────────────────────
        if "source" in item:
            item["source"] = item["source"].lower()

        # ── Strip ImagesPipeline internal fields ──────────────────────
        item.pop("image_urls", None)
        item.pop("images", None)

        logger.debug("transform.done", spider=spider.name, url=url)
        return item


def _parse_price(value: str) -> float | None:
    """Extract a numeric price from strings like '£12.34' or '$1,200.00'."""
    match = re.search(r"[\d,]+\.?\d*", value.replace(",", ""))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None
