"""Database loader pipeline — persist scraped items to PostgreSQL.

Runs at priority 300, after extract and transform stages.
Uses SQLAlchemy ORM with upsert-on-conflict to avoid duplicates across runs.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert

from data_models import Product, JobListing, SessionLocal

logger = structlog.get_logger(__name__)


class DatabasePipeline:
    """Write cleaned items to the database."""

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self) -> None:
        self.session = SessionLocal()

    def close_spider(self) -> None:
        self.session.close()

    def process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        spider_name: str = self.crawler.spider.name

        if spider_name == "products":
            self._upsert_product(item)
        elif spider_name == "jobs":
            self._upsert_job(item)
        else:
            logger.warning("load.unknown_spider", spider=spider_name)

        return item

    # ── Private helpers ──────────────────────────────────────────────

    def _upsert_product(self, item: dict[str, Any]) -> None:
        stmt = (
            pg_insert(Product)
            .values(
                title=item.get("title"),
                price=item.get("price"),
                currency=item.get("currency", "USD"),
                description=item.get("description"),
                url=item["url"],
                image_url=item.get("image_url"),
                source=item.get("source", ""),
                location=item.get("location"),
                category=item.get("category"),
            )
            .on_conflict_do_update(
                index_elements=["url"],
                set_={"title": item.get("title"), "price": item.get("price")},
            )
        )
        self.session.execute(stmt)
        self.session.commit()
        logger.info("load.product", url=item["url"])

    def _upsert_job(self, item: dict[str, Any]) -> None:
        stmt = (
            pg_insert(JobListing)
            .values(
                title=item.get("title"),
                company=item.get("company"),
                location=item.get("location"),
                description=item.get("description"),
                url=item["url"],
                source=item.get("source", ""),
                posted_at=item.get("posted_at"),
            )
            .on_conflict_do_update(
                index_elements=["url"],
                set_={"title": item.get("title"), "company": item.get("company")},
            )
        )
        self.session.execute(stmt)
        self.session.commit()
        logger.info("load.job", url=item["url"])
