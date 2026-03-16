"""Database session and engine helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from configs import get_settings

settings = get_settings()

engine = create_engine(
    settings.database.url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, ensuring it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
