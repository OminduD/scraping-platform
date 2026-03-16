"""Pydantic schemas for analytics responses."""

from __future__ import annotations

from pydantic import BaseModel


class SourceCount(BaseModel):
    source: str
    count: int


class AnalyticsSummary(BaseModel):
    total_products: int
    total_jobs: int
    products_by_source: list[SourceCount]
    jobs_by_source: list[SourceCount]
    avg_product_price: float | None = None
