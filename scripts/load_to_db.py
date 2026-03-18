"""Manually load scraped JSON data into PostgreSQL.

Usage:
    python -m scripts.load_to_db data/processed/products.json --type product
    python -m scripts.load_to_db data/processed/jobs.json --type job
    python -m scripts.load_to_db data/raw/products_raw_*.json --type product

Reads a JSON file produced by the scrapy FEEDS export, applies the same
transform logic (dedup, price parsing, normalization), then upserts into
the PostgreSQL database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert

from data_models import Base, Product, JobListing, engine, SessionLocal
from pipelines.transform.cleaner import _parse_price


def load_json(path: Path) -> list[dict]:
    """Read a JSON array from disk."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    return data


def clean_record(record: dict, item_type: str) -> dict:
    """Apply the same transforms the Scrapy pipeline does."""
    # Strip whitespace from text fields
    for field in ("title", "company", "location", "description"):
        val = record.get(field)
        if isinstance(val, str):
            record[field] = val.strip()

    # Parse price
    if item_type == "product":
        raw_price = record.get("price")
        if isinstance(raw_price, str):
            record["price"] = _parse_price(raw_price)

    # Normalize source
    if "source" in record:
        record["source"] = record["source"].lower()

    # Remove internal fields
    record.pop("image_urls", None)
    record.pop("images", None)
    record.pop("availability", None)
    record.pop("rating", None)

    return record


def upsert_products(session, records: list[dict]) -> int:
    count = 0
    for rec in records:
        stmt = (
            pg_insert(Product)
            .values(
                title=rec.get("title"),
                price=rec.get("price"),
                currency=rec.get("currency", "USD"),
                description=rec.get("description"),
                url=rec["url"],
                image_url=rec.get("image_url"),
                source=rec.get("source", ""),
                location=rec.get("location"),
                category=rec.get("category"),
            )
            .on_conflict_do_update(
                index_elements=["url"],
                set_={"title": rec.get("title"), "price": rec.get("price")},
            )
        )
        session.execute(stmt)
        count += 1
    return count


def upsert_jobs(session, records: list[dict]) -> int:
    count = 0
    for rec in records:
        stmt = (
            pg_insert(JobListing)
            .values(
                title=rec.get("title"),
                company=rec.get("company"),
                location=rec.get("location"),
                description=rec.get("description"),
                url=rec["url"],
                source=rec.get("source", ""),
                posted_at=rec.get("posted_at"),
            )
            .on_conflict_do_update(
                index_elements=["url"],
                set_={"title": rec.get("title"), "company": rec.get("company")},
            )
        )
        session.execute(stmt)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load scraped JSON data into PostgreSQL"
    )
    parser.add_argument("json_file", help="Path to the JSON file to load")
    parser.add_argument(
        "--type",
        required=True,
        choices=["product", "job"],
        help="Type of data: product or job",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and clean data but don't write to DB",
    )
    args = parser.parse_args()

    path = Path(args.json_file)
    if not path.is_file():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    records = load_json(path)
    print(f"Loaded {len(records)} records from {path}")

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_records = []
    for rec in records:
        url = rec.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_records.append(clean_record(rec, args.type))
    print(f"After dedup: {len(unique_records)} unique records")

    if args.dry_run:
        for rec in unique_records[:5]:
            print(f"  {rec.get('title', 'N/A')} — {rec.get('url', 'N/A')}")
        if len(unique_records) > 5:
            print(f"  ... and {len(unique_records) - 5} more")
        print("Dry run complete. No data written to database.")
        return

    session = SessionLocal()
    try:
        if args.type == "product":
            count = upsert_products(session, unique_records)
        else:
            count = upsert_jobs(session, unique_records)
        session.commit()
        print(f"Successfully loaded {count} {args.type}(s) into the database.")
    except Exception as exc:
        session.rollback()
        print(f"Error loading data: {exc}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
