"""Database loader pipeline — persist scraped items to PostgreSQL.

Runs at priority 300, after extract and transform stages.
Uses SQLAlchemy ORM with upsert-on-conflict to avoid duplicates across runs.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from data_models import Product, JobListing, SessionLocal

logger = structlog.get_logger(__name__)


class DatabasePipeline:
    """Write cleaned items to the database."""

    def __init__(self) -> None:
        self.enabled = True
        self.session = None

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self, spider) -> None:
        try:
            self.session = SessionLocal()
            # Force an early connectivity check to avoid failing per-item later.
            self.session.execute(text("SELECT 1"))
        except OperationalError as exc:
            self.enabled = False
            if self.session is not None:
                self.session.close()
                self.session = None
            logger.warning("load.db_unavailable", spider=spider.name, error=str(exc))

    def close_spider(self, spider) -> None:
        if self.session is not None:
            self.session.close()

    def process_item(self, item: dict[str, Any], spider) -> dict[str, Any]:
        if not self.enabled or self.session is None:
            return item

        spider_name: str = spider.name

        try:
            if spider_name == "products":
                self._upsert_product(item)
            elif spider_name == "jobs":
                self._upsert_job(item)
            else:
                logger.warning("load.unknown_spider", spider=spider_name)
        except OperationalError as exc:
            # Fail open: disable DB writes for the rest of the crawl but keep item flow.
            self.enabled = False
            self.session.rollback()
            logger.warning("load.db_disabled", spider=spider_name, error=str(exc))
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("load.db_write_failed", spider=spider_name, error=str(exc))

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
