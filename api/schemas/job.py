"""Pydantic schemas for JobListing responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str | None = None
    location: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = "USD"
    description: str | None = None
    url: str
    source: str
    posted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
