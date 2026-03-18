"""Standalone ETL runner — can be used outside of Scrapy pipelines.

Usage:
    python -m pipelines.etl_runner --input data/raw/products_20260318_065708.json --type product
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import structlog

from data_models import JobListing, Product, SessionLocal
from pipelines.transform.cleaner import _parse_price

logger = structlog.get_logger(__name__)


def extract(path: Path) -> list[dict]:
    """Read raw JSON from disk (array/object, with JSONL fallback)."""
    text = path.read_text(encoding="utf-8")

    if not text.strip():
        data = []
    else:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("Unsupported JSON root type. Expected object or array.")
        except json.JSONDecodeError:
            # Support JSONL files (one JSON object per line)
            data = []
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                obj = json.loads(stripped)
                if not isinstance(obj, dict):
                    raise ValueError("Invalid JSONL format. Each line must be a JSON object.")
                data.append(obj)

    logger.info("etl.extract", records=len(data), path=str(path))
    return data


def transform(records: list[dict], item_type: str) -> pd.DataFrame:
    """Clean, deduplicate, and normalize records using Pandas."""
    df = pd.DataFrame(records)

    # Drop exact duplicates
    df = df.drop_duplicates(subset=["url"], keep="last")

    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # Normalize price for products
    if item_type == "product" and "price" in df.columns:
        df["price"] = df["price"].apply(
            lambda v: _parse_price(v) if isinstance(v, str) else v
        )

    # Lowercase source
    if "source" in df.columns:
        df["source"] = df["source"].str.lower()

    logger.info("etl.transform", records=len(df), item_type=item_type)
    return df


def load(df: pd.DataFrame, item_type: str) -> int:
    """Insert transformed records into PostgreSQL."""
    session = SessionLocal()
    count = 0
    try:
        model = Product if item_type == "product" else JobListing
        for _, row in df.iterrows():
            record = model(**{k: v for k, v in row.to_dict().items() if pd.notna(v)})
            session.merge(record)
            count += 1
        session.commit()
        logger.info("etl.load", inserted=count, item_type=item_type)
    finally:
        session.close()
    return count


def run_etl(path: Path, item_type: str) -> int:
    records = extract(path)
    df = transform(records, item_type)
    return load(df, item_type)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ETL pipeline")
    parser.add_argument("--input", required=True, help="Path to raw JSON file")
    parser.add_argument("--type", required=True, choices=["product", "job"])
    args = parser.parse_args()
    run_etl(Path(args.input), args.type)
