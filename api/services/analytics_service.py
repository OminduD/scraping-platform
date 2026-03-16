"""Analytics service — aggregate queries."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.schemas.analytics import AnalyticsSummary, SourceCount
from data_models import Product, JobListing


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self) -> AnalyticsSummary:
        total_products = self.db.query(func.count(Product.id)).scalar() or 0
        total_jobs = self.db.query(func.count(JobListing.id)).scalar() or 0

        products_by_source = [
            SourceCount(source=row[0], count=row[1])
            for row in (
                self.db.query(Product.source, func.count(Product.id))
                .group_by(Product.source)
                .all()
            )
        ]

        jobs_by_source = [
            SourceCount(source=row[0], count=row[1])
            for row in (
                self.db.query(JobListing.source, func.count(JobListing.id))
                .group_by(JobListing.source)
                .all()
            )
        ]

        avg_price = self.db.query(func.avg(Product.price)).scalar()

        return AnalyticsSummary(
            total_products=total_products,
            total_jobs=total_jobs,
            products_by_source=products_by_source,
            jobs_by_source=jobs_by_source,
            avg_product_price=float(avg_price) if avg_price else None,
        )
