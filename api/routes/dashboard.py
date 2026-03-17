"""Dashboard routes — web UI for viewing scraped data."""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api.services.product_service import ProductService
from api.services.job_service import JobService
from api.services.analytics_service import AnalyticsService
from data_models import get_db

router = APIRouter()

DEFAULT_LIMIT = 100


def _page_shell(title: str, body: str, nav_active: str = "") -> str:
    """Wrap body content in a full HTML page with navigation."""

    def _nav_cls(name: str) -> str:
        return "active" if name == nav_active else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — Scraping Platform</title>
<style>
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background:#f8f9fa; color:#212529; }}
  nav{{ background:#343a40; padding:.8rem 2rem; display:flex; gap:1.5rem; align-items:center; }}
  nav a{{ color:#adb5bd; text-decoration:none; font-weight:500; }}
  nav a:hover,nav a.active{{ color:#fff; }}
  nav .brand{{ color:#fff; font-size:1.1rem; font-weight:700; margin-right:2rem; }}
  .container{{ max-width:1400px; margin:2rem auto; padding:0 2rem; }}
  h1{{ margin-bottom:1rem; }}
  .meta{{ color:#6c757d; margin-bottom:1rem; }}
  table{{ border-collapse:collapse; width:100%; background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.1); margin-top:1rem; }}
  th,td{{ padding:.6rem .8rem; text-align:left; border-bottom:1px solid #dee2e6; font-size:.9rem; }}
  th{{ background:#343a40; color:#fff; position:sticky; top:0; }}
  tr:hover{{ background:#f1f3f5; }}
  td{{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .card-grid{{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:1.5rem; }}
  .card{{ background:#fff; border-radius:8px; padding:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,.1); }}
  .card h2{{ font-size:1.1rem; margin-bottom:.5rem; }}
  .card .stat{{ font-size:2rem; font-weight:700; color:#0d6efd; }}
  img.thumb{{ max-width:60px; max-height:60px; object-fit:cover; border-radius:4px; }}
  a.btn{{ display:inline-block; padding:.4rem 1rem; background:#0d6efd; color:#fff; text-decoration:none; border-radius:4px; font-size:.85rem; margin-right:.4rem; margin-top:.4rem; }}
  a.btn:hover{{ background:#0b5ed7; }}
  .pagination{{ margin-top:1rem; }}
</style>
</head>
<body>
<nav>
  <span class="brand">Scraping Platform</span>
  <a href="/dashboard/" class="{_nav_cls("home")}">Home</a>
  <a href="/dashboard/products" class="{_nav_cls("products")}">Products</a>
  <a href="/dashboard/jobs" class="{_nav_cls("jobs")}">Jobs</a>
</nav>
<div class="container">
{body}
</div>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
def dashboard_home(db: Session = Depends(get_db)):
    """Dashboard landing page with summary cards and export links."""
    summary = AnalyticsService(db).summary()

    sources_html = ""
    for sc in summary.products_by_source:
        sources_html += f"<li>{escape(sc.source)}: {sc.count}</li>"
    for sc in summary.jobs_by_source:
        sources_html += f"<li>{escape(sc.source)}: {sc.count}</li>"

    body = f"""
<h1>Dashboard</h1>
<div class="card-grid">
  <div class="card">
    <h2>Products</h2>
    <div class="stat">{summary.total_products}</div>
    <p class="meta">Total scraped products</p>
    <a href="/dashboard/products" class="btn">View all</a>
  </div>
  <div class="card">
    <h2>Jobs</h2>
    <div class="stat">{summary.total_jobs}</div>
    <p class="meta">Total scraped jobs</p>
    <a href="/dashboard/jobs" class="btn">View all</a>
  </div>
  <div class="card">
    <h2>Avg. Product Price</h2>
    <div class="stat">{f"${summary.avg_product_price:,.2f}" if summary.avg_product_price else "N/A"}</div>
  </div>
</div>
<h2 style="margin-top:2rem;">Export Data</h2>
<div class="card-grid" style="margin-top:1rem;">
  <div class="card">
    <h2>Products</h2>
    <a href="/export/products/csv" class="btn">CSV</a>
    <a href="/export/products/tsv" class="btn">TSV</a>
    <a href="/export/products/html" class="btn">HTML</a>
  </div>
  <div class="card">
    <h2>Jobs</h2>
    <a href="/export/jobs/csv" class="btn">CSV</a>
    <a href="/export/jobs/tsv" class="btn">TSV</a>
    <a href="/export/jobs/html" class="btn">HTML</a>
  </div>
</div>
{f'<h2 style="margin-top:2rem;">Sources</h2><ul style="margin-top:.5rem;">{sources_html}</ul>' if sources_html else ""}
"""
    return _page_shell("Dashboard", body, nav_active="home")


@router.get("/products", response_class=HTMLResponse)
def dashboard_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    source: str | None = None,
    db: Session = Depends(get_db),
):
    """Product listing dashboard page."""
    svc = ProductService(db)
    products = svc.list_products(skip=skip, limit=limit, source=source)

    if not products:
        table_html = "<p>No products found.</p>"
    else:
        rows = []
        for p in products:
            img_cell = (
                f'<img class="thumb" src="{escape(p.image_url)}" alt="">'
                if p.image_url
                else ""
            )
            rows.append(
                f"<tr>"
                f"<td>{p.id}</td>"
                f"<td>{img_cell}</td>"
                f"<td>{escape(p.title)}</td>"
                f"<td>{p.price if p.price is not None else ''}</td>"
                f"<td>{escape(p.currency)}</td>"
                f"<td>{escape(p.source)}</td>"
                f'<td><a href="{escape(p.url)}" target="_blank">link</a></td>'
                f"<td>{p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''}</td>"
                f"</tr>"
            )
        table_html = (
            "<table>"
            "<thead><tr>"
            "<th>ID</th><th>Image</th><th>Title</th><th>Price</th>"
            "<th>Currency</th><th>Source</th><th>URL</th><th>Created</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )

    source_param = f"&source={escape(source)}" if source else ""
    prev_skip = max(0, skip - limit)
    next_skip = skip + limit
    pagination = (
        '<div class="pagination">'
        + (
            f'<a class="btn" href="/dashboard/products?skip={prev_skip}&limit={limit}{source_param}">Previous</a>'
            if skip > 0
            else ""
        )
        + f'<a class="btn" href="/dashboard/products?skip={next_skip}&limit={limit}{source_param}">Next</a>'
        + "</div>"
    )

    body = (
        f"<h1>Products</h1>"
        f'<p class="meta">Showing {len(products)} products (offset {skip})</p>'
        f"{table_html}"
        f"{pagination}"
    )
    return _page_shell("Products", body, nav_active="products")


@router.get("/jobs", response_class=HTMLResponse)
def dashboard_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    source: str | None = None,
    db: Session = Depends(get_db),
):
    """Job listing dashboard page."""
    svc = JobService(db)
    jobs = svc.list_jobs(skip=skip, limit=limit, source=source)

    if not jobs:
        table_html = "<p>No jobs found.</p>"
    else:
        rows = []
        for j in jobs:
            rows.append(
                f"<tr>"
                f"<td>{j.id}</td>"
                f"<td>{escape(j.title)}</td>"
                f"<td>{escape(j.company or '')}</td>"
                f"<td>{escape(j.location or '')}</td>"
                f"<td>{escape(j.source)}</td>"
                f'<td><a href="{escape(j.url)}" target="_blank">link</a></td>'
                f"<td>{j.created_at.strftime('%Y-%m-%d %H:%M') if j.created_at else ''}</td>"
                f"</tr>"
            )
        table_html = (
            "<table>"
            "<thead><tr>"
            "<th>ID</th><th>Title</th><th>Company</th><th>Location</th>"
            "<th>Source</th><th>URL</th><th>Created</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )

    source_param = f"&source={escape(source)}" if source else ""
    prev_skip = max(0, skip - limit)
    next_skip = skip + limit
    pagination = (
        '<div class="pagination">'
        + (
            f'<a class="btn" href="/dashboard/jobs?skip={prev_skip}&limit={limit}{source_param}">Previous</a>'
            if skip > 0
            else ""
        )
        + f'<a class="btn" href="/dashboard/jobs?skip={next_skip}&limit={limit}{source_param}">Next</a>'
        + "</div>"
    )

    body = (
        f"<h1>Job Listings</h1>"
        f'<p class="meta">Showing {len(jobs)} jobs (offset {skip})</p>'
        f"{table_html}"
        f"{pagination}"
    )
    return _page_shell("Jobs", body, nav_active="jobs")
