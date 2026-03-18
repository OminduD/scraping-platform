"""Scrapy pipeline that exports scraped data as JSON on spider close."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import time

import structlog

logger = structlog.get_logger(__name__)

OUTPUT_DIR = Path("data/raw")


class JsonExportPipeline:
    """Collect items during crawl and write a JSON file when the spider closes."""

    checkpoint_every = 25
    checkpoint_seconds = 10.0

    def __init__(self) -> None:
        self.items: list[dict] = []
        self.path: Path | None = None
        self._processed_count = 0
        self._last_checkpoint_ts = 0.0

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self, spider) -> None:
        spider_name = spider.name
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{spider_name}_{timestamp}.json"
        self.path = OUTPUT_DIR / filename

        # Create the file immediately so interrupted crawls still leave an artifact.
        self._write_snapshot()
        logger.info("json_export.open", spider=spider_name, path=str(self.path))

    def process_item(self, item, spider):
        self.items.append(dict(item))
        self._processed_count += 1
        now = time.monotonic()
        elapsed = now - self._last_checkpoint_ts

        # Persist the first item quickly, then checkpoint periodically for long crawls.
        if (
            self._processed_count == 1
            or self._processed_count % self.checkpoint_every == 0
            or elapsed >= self.checkpoint_seconds
        ):
            self._write_snapshot()
            self._last_checkpoint_ts = now
            logger.info(
                "json_export.checkpoint",
                spider=spider.name,
                path=str(self.path),
                count=len(self.items),
            )

        return item

    def close_spider(self, spider) -> None:
        spider_name = spider.name
        if self.path is None:
            self.open_spider(spider)

        if not self.items:
            logger.info("json_export.no_items", spider=spider_name, path=str(self.path))

        self._write_snapshot()
        logger.info("json_export.done", spider=spider_name, path=str(self.path), count=len(self.items))

    def _write_snapshot(self) -> None:
        if self.path is None:
            return
        self.path.write_text(
            json.dumps(self.items, default=str, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
