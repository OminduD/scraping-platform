"""Product model — represents a scraped product listing."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Float, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from data_models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} title={self.title!r}>"
