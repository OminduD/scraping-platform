"""Scrapy pipeline that exports scraped data as JSON on spider close."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

OUTPUT_DIR = Path("data/raw")


class JsonExportPipeline:
    """Collect items during crawl and write a JSON file when the spider closes."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider) -> None:
        spider_name = spider.name
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{spider_name}_{timestamp}.json"
        path = OUTPUT_DIR / filename

        if not self.items:
            logger.info("json_export.no_items", spider=spider_name, path=str(path))

        path.write_text(
            json.dumps(self.items, default=str, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("json_export.done", spider=spider_name, path=str(path), count=len(self.items))
