"""Export endpoints — download products/jobs as CSV or HTML."""

from __future__ import annotations

import csv
import io
from html import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.services.product_service import ProductService
from api.services.job_service import JobService
from data_models import get_db

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
