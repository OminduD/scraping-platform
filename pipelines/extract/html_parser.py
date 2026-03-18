"""HTML parsing / cleanup pipeline stage.

This Scrapy pipeline runs first (priority 100) and ensures raw HTML fragments
embedded in item fields are converted to clean plain text.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)


class HtmlCleanPipeline:
    """Strip HTML tags and collapse whitespace in string fields."""

    # Fields that may contain HTML fragments
    HTML_FIELDS = {"description", "title", "company"}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def process_item(self, item: dict[str, Any], spider) -> dict[str, Any]:
        for field in self.HTML_FIELDS:
            raw = item.get(field)
            if raw and isinstance(raw, str) and "<" in raw:
                cleaned = BeautifulSoup(raw, "lxml").get_text(separator=" ")
                item[field] = _collapse_whitespace(cleaned)
                logger.debug("extract.html_clean", field=field, spider=spider.name)
        return item


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
