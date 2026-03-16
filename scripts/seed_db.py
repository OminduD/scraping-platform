"""Seed the database with sample data for development."""

from __future__ import annotations

from datetime import datetime, timezone

from data_models import Base, Product, JobListing, engine, SessionLocal


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    products = [
        Product(
            title="Python Crash Course",
            price=29.99,
            currency="USD",
            url="https://example.com/product/python-crash-course",
            source="example.com",
            category="Books",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Product(
            title="Mechanical Keyboard",
            price=89.99,
            currency="USD",
            url="https://example.com/product/mech-keyboard",
            source="example.com",
            category="Electronics",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    jobs = [
        JobListing(
            title="Senior Data Engineer",
            company="DataCo",
            location="Remote",
            salary_min=120000,
            salary_max=160000,
            url="https://example.com/job/senior-data-engineer",
            source="example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        JobListing(
            title="Backend Developer",
            company="TechStartup",
            location="San Francisco, CA",
            salary_min=100000,
            salary_max=140000,
            url="https://example.com/job/backend-developer",
            source="example.com",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    for item in products + jobs:
        session.merge(item)

    session.commit()
    session.close()
    print(f"Seeded {len(products)} products and {len(jobs)} jobs.")


if __name__ == "__main__":
    seed()
