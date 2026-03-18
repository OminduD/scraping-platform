"""Export endpoints — download products/jobs as CSV, TSV, PSV, or HTML.

Also provides endpoints to load raw JSON data into PostgreSQL.
"""

from __future__ import annotations

import csv
import io
import json
from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.services.product_service import ProductService
from api.services.job_service import JobService
from data_models import get_db, Product, JobListing
from pipelines.transform.cleaner import _parse_price

router = APIRouter()

MAX_EXPORT_ROWS = 10_000


# ── helpers ──────────────────────────────────────────────────────────


def _rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _rows_to_tsv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _rows_to_psv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys(), delimiter="|")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _rows_to_html(rows: list[dict], title: str) -> str:
    if not rows:
        headers_html = ""
        body_html = "<tr><td>No data available</td></tr>"
    else:
        headers = list(rows[0].keys())
        headers_html = "".join(f"<th>{escape(h)}</th>" for h in headers)
        body_parts = []
        for row in rows:
            cells = "".join(
                f"<td>{escape(str(v))}</td>" for v in row.values()
            )
            body_parts.append(f"<tr>{cells}</tr>")
        body_html = "".join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; background: #f8f9fa; }}
  h1 {{ color: #212529; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  th, td {{ padding: .6rem .8rem; text-align: left; border-bottom: 1px solid #dee2e6; }}
  th {{ background: #343a40; color: #fff; position: sticky; top: 0; }}
  tr:hover {{ background: #f1f3f5; }}
  .meta {{ color: #6c757d; margin-bottom: 1rem; }}
</style>
</head>
<body>
<h1>{escape(title)}</h1>
<p class="meta">{len(rows)} items</p>
<table>
<thead><tr>{headers_html}</tr></thead>
<tbody>{body_html}</tbody>
</table>
</body>
</html>"""


def _product_to_dict(p) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "price": p.price,
        "currency": p.currency,
        "description": p.description or "",
        "url": p.url,
        "image_url": p.image_url or "",
        "source": p.source,
        "location": p.location or "",
        "category": p.category or "",
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
    }


def _job_to_dict(j) -> dict:
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company or "",
        "location": j.location or "",
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "currency": j.currency,
        "description": j.description or "",
        "url": j.url,
        "source": j.source,
        "posted_at": str(j.posted_at) if j.posted_at else "",
        "created_at": str(j.created_at),
        "updated_at": str(j.updated_at),
    }


# ── product exports ─────────────────────────────────────────────────


@router.get("/products/csv")
def export_products_csv(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all products as a CSV file."""
    svc = ProductService(db)
    products = svc.list_products(skip=0, limit=limit, source=source)
    rows = [_product_to_dict(p) for p in products]
    content = _rows_to_csv(rows)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.get("/products/html")
def export_products_html(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all products as an HTML file."""
    svc = ProductService(db)
    products = svc.list_products(skip=0, limit=limit, source=source)
    rows = [_product_to_dict(p) for p in products]
    content = _rows_to_html(rows, "Products — Scraped Results")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": "attachment; filename=products.html"},
    )


@router.get("/products/tsv")
def export_products_tsv(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all products as a TSV file."""
    svc = ProductService(db)
    products = svc.list_products(skip=0, limit=limit, source=source)
    rows = [_product_to_dict(p) for p in products]
    content = _rows_to_tsv(rows)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": "attachment; filename=products.tsv"},
    )


@router.get("/products/psv")
def export_products_psv(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all products as a PSV (pipe-separated values) file."""
    svc = ProductService(db)
    products = svc.list_products(skip=0, limit=limit, source=source)
    rows = [_product_to_dict(p) for p in products]
    content = _rows_to_psv(rows)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=products.psv"},
    )


# ── job exports ──────────────────────────────────────────────────────


@router.get("/jobs/csv")
def export_jobs_csv(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all jobs as a CSV file."""
    svc = JobService(db)
    jobs = svc.list_jobs(skip=0, limit=limit, source=source)
    rows = [_job_to_dict(j) for j in jobs]
    content = _rows_to_csv(rows)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs.csv"},
    )


@router.get("/jobs/html")
def export_jobs_html(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all jobs as an HTML file."""
    svc = JobService(db)
    jobs = svc.list_jobs(skip=0, limit=limit, source=source)
    rows = [_job_to_dict(j) for j in jobs]
    content = _rows_to_html(rows, "Job Listings — Scraped Results")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": "attachment; filename=jobs.html"},
    )


@router.get("/jobs/tsv")
def export_jobs_tsv(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all jobs as a TSV file."""
    svc = JobService(db)
    jobs = svc.list_jobs(skip=0, limit=limit, source=source)
    rows = [_job_to_dict(j) for j in jobs]
    content = _rows_to_tsv(rows)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": "attachment; filename=jobs.tsv"},
    )


@router.get("/jobs/psv")
def export_jobs_psv(
    source: str | None = None,
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
    db: Session = Depends(get_db),
):
    """Download all jobs as a PSV (pipe-separated values) file."""
    svc = JobService(db)
    jobs = svc.list_jobs(skip=0, limit=limit, source=source)
    rows = [_job_to_dict(j) for j in jobs]
    content = _rows_to_psv(rows)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=jobs.psv"},
    )


# ── Load to PostgreSQL ───────────────────────────────────────────────

RAW_DATA_DIR = Path("data/raw")


def _clean_record(record: dict, item_type: str) -> dict:
    """Apply the same transforms the Scrapy pipeline does."""
    for field in ("title", "company", "location", "description"):
        val = record.get(field)
        if isinstance(val, str):
            record[field] = val.strip()

    if item_type == "product":
        raw_price = record.get("price")
        if isinstance(raw_price, str):
            record["price"] = _parse_price(raw_price)

    if "source" in record:
        record["source"] = record["source"].lower()

    record.pop("image_urls", None)
    record.pop("images", None)
    record.pop("availability", None)
    record.pop("rating", None)

    return record


def _upsert_products(session: Session, records: list[dict]) -> int:
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
    session.commit()
    return count


def _upsert_jobs(session: Session, records: list[dict]) -> int:
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
    session.commit()
    return count


@router.get("/raw-files")
def list_raw_files():
    """List available raw JSON files that can be loaded into PostgreSQL."""
    if not RAW_DATA_DIR.exists():
        return {"files": []}

    files = []
    for f in sorted(RAW_DATA_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        item_type = "job" if "job" in f.name.lower() else "product"
        files.append({
            "name": f.name,
            "path": str(f),
            "type": item_type,
            "size": f.stat().st_size,
        })
    return {"files": files}


@router.post("/load-to-db")
def load_to_postgresql(
    filename: str = Query(..., description="Name of the raw JSON file to load"),
    item_type: str = Query(..., pattern="^(product|job)$", description="Type of data: product or job"),
    db: Session = Depends(get_db),
):
    """Load a raw JSON file into PostgreSQL database."""
    file_path = RAW_DATA_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    if not file_path.suffix == ".json":
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_records = []
    for rec in data:
        url = rec.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_records.append(_clean_record(rec, item_type))

    try:
        if item_type == "product":
            count = _upsert_products(db, unique_records)
        else:
            count = _upsert_jobs(db, unique_records)

        return JSONResponse({
            "ok": True,
            "message": f"Successfully loaded {count} {item_type}(s) into PostgreSQL",
            "loaded": count,
            "file": filename,
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# ── Raw file exports ──────────────────────────────────────────────────


def _load_raw_json(filename: str) -> list[dict]:
    """Load raw JSON file and return list of records."""
    file_path = RAW_DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    text = file_path.read_text(encoding="utf-8")
    if not text.strip():
        return []

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="Invalid JSON: expected array or object at root")
        return data
    except json.JSONDecodeError:
        # Fallback for JSON Lines files
        rows: list[dict] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                raise HTTPException(status_code=400, detail="Invalid JSON Lines: each line must be a JSON object")
        return rows


@router.get("/raw/{filename}/csv")
def export_raw_csv(filename: str):
    """Download raw JSON file as CSV."""
    rows = _load_raw_json(filename)
    content = _rows_to_csv(rows)
    csv_filename = filename.replace(".json", ".csv")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={csv_filename}"},
    )


@router.get("/raw/{filename}/tsv")
def export_raw_tsv(filename: str):
    """Download raw JSON file as TSV."""
    rows = _load_raw_json(filename)
    content = _rows_to_tsv(rows)
    tsv_filename = filename.replace(".json", ".tsv")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": f"attachment; filename={tsv_filename}"},
    )


@router.get("/raw/{filename}/psv")
def export_raw_psv(filename: str):
    """Download raw JSON file as PSV."""
    rows = _load_raw_json(filename)
    content = _rows_to_psv(rows)
    psv_filename = filename.replace(".json", ".psv")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={psv_filename}"},
    )


@router.get("/raw/{filename}/html")
def export_raw_html(filename: str):
    """Download raw JSON file as HTML table."""
    rows = _load_raw_json(filename)
    content = _rows_to_html(rows, f"Raw Data — {filename}")
    html_filename = filename.replace(".json", ".html")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={html_filename}"},
    )


@router.get("/raw/{filename}/json")
def export_raw_json(filename: str):
    """Download raw JSON file as-is."""
    rows = _load_raw_json(filename)
    content = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/raw/{filename}/preview")
def preview_raw_file(
    filename: str,
    limit: int = Query(20, ge=1, le=100, description="Number of items to preview"),
):
    """Get preview data from raw JSON file for dashboard display."""
    rows = _load_raw_json(filename)
    return {
        "filename": filename,
        "total": len(rows),
        "preview_count": min(limit, len(rows)),
        "items": rows[:limit],
    }
