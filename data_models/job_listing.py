"""JobListing model — represents a scraped job posting."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Float, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from data_models.base import Base


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<JobListing id={self.id} title={self.title!r}>"
