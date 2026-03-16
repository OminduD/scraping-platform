"""Pydantic schemas for Product responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: float | None = None
    currency: str = "USD"
    description: str | None = None
    url: str
    image_url: str | None = None
    source: str
    location: str | None = None
    category: str | None = None
    created_at: datetime
    updated_at: datetime
