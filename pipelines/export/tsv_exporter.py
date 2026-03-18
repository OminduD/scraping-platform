"""Scrapy pipeline that exports clean tabular data as TSV on spider close."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

OUTPUT_DIR = Path("data/processed")

SPIDER_OUTPUT_FILES = {
    "products": "products.tsv",
    "jobs": "jobs.tsv",
    "anix": "anix_products.tsv",
}

# Fields to include in the clean TSV (ordered)
PRODUCT_FIELDS = ["title", "price", "url", "image_url", "source", "location", "category"]
JOB_FIELDS = ["title", "company", "location", "posted_at", "url", "source"]

SPIDER_FIELDS = {
    "products": PRODUCT_FIELDS,
    "jobs": JOB_FIELDS,
    "anix": PRODUCT_FIELDS,
}


class TsvExportPipeline:
    """Collect items during crawl and write a clean TSV file when the spider closes."""

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
        filename = SPIDER_OUTPUT_FILES.get(spider_name)
        if not filename:
            logger.warning("tsv_export.unknown_spider", spider=spider_name)
            return

        if not self.items:
            logger.info("tsv_export.no_items", spider=spider_name)
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / filename

        fields = SPIDER_FIELDS.get(spider_name, list(self.items[0].keys()))

        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=fields,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(self.items)

        path.write_text(buf.getvalue(), encoding="utf-8")
        logger.info("tsv_export.done", spider=spider_name, path=str(path), count=len(self.items))
