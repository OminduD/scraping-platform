"""Dashboard routes — web UI for viewing scraped data."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api.services.product_service import ProductService
from api.services.job_service import JobService
from api.services.analytics_service import AnalyticsService
from data_models import get_db

router = APIRouter()

DEFAULT_LIMIT = 100
RAW_OUTPUT_DIR = Path("data/raw")


def _render_raw_preview_table(items: list[dict]) -> str:
    """Render raw scraped items as an HTML table with images and clickable links."""
    if not items:
        return "<p>No items to display.</p>"

    def _is_image_field(key: str) -> bool:
        """Check if field name suggests it contains an image URL."""
        k = key.lower()
        return k in ("image_url", "image", "img_url", "thumbnail", "photo", "picture")

    def _is_image_url(url: str) -> bool:
        """Check if URL points to an image file."""
        if not url or not isinstance(url, str):
            return False
        lower_url = url.lower()
        return any(lower_url.endswith(ext) or f"{ext}?" in lower_url
                   for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"))

    # Collect all unique keys across all items
    all_keys: list[str] = []
    for item in items:
        for k in item.keys():
            if k not in all_keys:
                all_keys.append(k)

    # Prioritize common fields
    priority = ["image_url", "image", "thumbnail", "title", "price", "url", "company", "location", "source"]
    ordered_keys = [k for k in priority if k in all_keys]
    ordered_keys += [k for k in all_keys if k not in priority]

    headers = "".join(f"<th>{escape(k)}</th>" for k in ordered_keys)
    rows_html = []
    for item in items:
        cells = []
        for k in ordered_keys:
            val = item.get(k, "")
            str_val = str(val) if val is not None else ""

            # Check if this is an image field or image URL - render as image
            if _is_image_field(k) and str_val.startswith("http"):
                cells.append(f'<td><img class="thumb" src="{escape(str_val)}" alt=""></td>')
            elif k == "url" and val:
                # Main URL field - render as clickable link
                cells.append(f'<td><a href="{escape(str_val)}" target="_blank">View</a></td>')
            elif _is_image_url(str_val):
                # Looks like an image URL - render as image
                cells.append(f'<td><img class="thumb" src="{escape(str_val)}" alt=""></td>')
            elif isinstance(val, str) and val.startswith("http"):
                # Any other URL field - make clickable
                display = val[:40] + "..." if len(val) > 40 else val
                cells.append(f'<td><a href="{escape(val)}" target="_blank">{escape(display)}</a></td>')
            else:
                # Regular value - escape and truncate if too long
                display_val = str_val[:100] + "..." if len(str_val) > 100 else str_val
                cells.append(f"<td>{escape(display_val)}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    return f"""
<table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
</table>
"""


def _load_raw_file_rows(filename: str) -> list[dict[str, Any]]:
    """Load raw rows from JSON or JSONL file under data/raw."""
    safe_name = Path(filename).name
    path = RAW_OUTPUT_DIR / safe_name

    if not path.exists() or path.suffix.lower() != ".json":
        raise FileNotFoundError(safe_name)

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    except json.JSONDecodeError:
        pass

    # Recover rows from partially written JSON arrays (e.g., interrupted checkpoint writes).
    decoder = json.JSONDecoder()
    partial_rows: list[dict[str, Any]] = []
    idx = text.find("[")
    if idx >= 0:
        idx += 1
        while idx < len(text):
            # Skip delimiters and whitespace between array elements.
            while idx < len(text) and text[idx] in " \t\r\n,]":
                idx += 1
            if idx >= len(text):
                break
            try:
                obj, idx = decoder.raw_decode(text, idx)
            except json.JSONDecodeError:
                break

            if isinstance(obj, dict):
                partial_rows.append(obj)
            elif isinstance(obj, list):
                partial_rows.extend(row for row in obj if isinstance(row, dict))

    if partial_rows:
        return partial_rows

    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            # Ignore malformed lines and keep whatever valid JSONL rows we can parse.
            continue
        if isinstance(obj, dict):
            rows.append(obj)

    if rows:
        return rows

    raise json.JSONDecodeError("Unable to parse JSON content", text, 0)


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
  button.btn{{ display:inline-block; padding:.4rem 1rem; background:#0d6efd; color:#fff; border:none; border-radius:4px; font-size:.85rem; margin-right:.4rem; margin-top:.4rem; cursor:pointer; }}
  button.btn:hover{{ background:#0b5ed7; }}
  .btn-success{{ background:#198754; }}
  .btn-success:hover{{ background:#157347; }}
  .pagination{{ margin-top:1rem; }}
  .export-btns{{ margin-top:1rem; margin-bottom:1rem; }}
</style>
</head>
<body>
<nav>
  <span class="brand">Scraping Platform</span>
  <a href="/dashboard/" class="{_nav_cls("home")}">Home</a>
  <a href="/dashboard/products" class="{_nav_cls("products")}">Products</a>
  <a href="/dashboard/jobs" class="{_nav_cls("jobs")}">Jobs</a>
  <a href="/dashboard/raw-scrape" class="{_nav_cls("raw_scrape")}">Raw Scrape</a>
</nav>
<div class="container">
{body}
</div>
</body>
</html>"""


def _run_raw_scrape(
    spider: str,
    url: str | None,
    use_sitemap: bool,
    sitemap_urls: list[str] | None,
    max_items: int,
) -> dict[str, Any]:
    """Run a spider and store raw scraped output in a JSON file."""
    # Keep file naming consistent with other raw exports: <spider>_YYYYMMDD_HHMMSS.json
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = RAW_OUTPUT_DIR / f"{spider}_{timestamp}.json"
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_spider",
        spider,
        "--output-json",
        str(output_file),
    ]
    if url:
        cmd.extend(["--url", url])
    if sitemap_urls:
        for sitemap_url in sitemap_urls:
            cmd.extend(["--sitemap-url", sitemap_url])
    elif use_sitemap:
        cmd.append("--sitemap")

    run = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        timeout=max(60, max_items * 2),
    )

    if run.returncode != 0:
        return {
            "ok": False,
            "error": (run.stderr or run.stdout or "Spider execution failed").strip(),
        }

    if not output_file.exists():
        return {
            "ok": False,
            "error": "Scrape finished but no JSON output file was created.",
        }

    try:
        payload = json.loads(output_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = []

    if not isinstance(payload, list):
        payload = []

    return {
        "ok": True,
        "file": str(output_file),
        "count": len(payload),
        "preview": payload[:max_items],
    }


# ── JSON API endpoints (for static frontend) ─────────────────────────────


@router.post("/raw-scrape")
def api_raw_scrape(
    spider: str = Form(...),
    url: str | None = Form(default=None),
    sitemap: bool = Form(default=False),
    sitemap_url: str | None = Form(default=None),
    preview_limit: int = Form(default=10),
):
    """Run a manual scrape and return JSON result."""
    if spider not in {"products", "jobs"}:
        return {"ok": False, "error": "Invalid spider selected. Choose 'products' or 'jobs'."}

    normalized_url = (url or "").strip() or None
    normalized_sitemap_url = (sitemap_url or "").strip() or None
    safe_preview_limit = max(1, min(preview_limit, 100))
    return _run_raw_scrape(
        spider=spider,
        url=normalized_url,
        use_sitemap=sitemap,
        sitemap_urls=[normalized_sitemap_url] if normalized_sitemap_url else None,
        max_items=safe_preview_limit,
    )


@router.get("/raw-files")
def api_raw_files():
    """List all raw JSON files in data/raw."""
    files = []
    if RAW_OUTPUT_DIR.exists():
        for f in sorted(RAW_OUTPUT_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
            })
    return {"files": files}


@router.get("/raw-preview/{filename:path}", response_class=HTMLResponse)
def dashboard_raw_file_preview(filename: str, limit: int = Query(20, ge=1, le=200)):
    """Display raw file preview as HTML table."""
    try:
        rows = _load_raw_file_rows(filename)
    except FileNotFoundError:
        body = f"<h1>Raw File Preview</h1><p class='meta' style='color:#b42318;'>File not found: {escape(filename)}</p>"
        return _page_shell("Preview Error", body, nav_active="raw_scrape")
    except json.JSONDecodeError as exc:
        body = f"<h1>Raw File Preview</h1><p class='meta' style='color:#b42318;'>Invalid JSON in {escape(filename)}: {escape(str(exc))}</p>"
        return _page_shell("Preview Error", body, nav_active="raw_scrape")

    safe_filename = Path(filename).name
    total_count = len(rows)
    preview_count = min(limit, total_count)
    preview_rows = rows[:limit]

    # Collect column info
    all_keys = []
    for item in preview_rows:
        for k in item.keys():
            if k not in all_keys:
                all_keys.append(k)

    table_html = _render_raw_preview_table(preview_rows)

    body = f"""
<h1>Raw Data Preview</h1>
<div class="card" style="margin-bottom:1rem;">
    <h2>{escape(safe_filename)}</h2>
    <p class="meta">Total Records: {total_count} | Showing: {preview_count} | Columns: {len(all_keys)}</p>
</div>
<div class="export-btns" style="margin-bottom:1rem;">
    <a href="/export/raw/{escape(safe_filename)}/csv" class="btn">Download CSV</a>
    <a href="/export/raw/{escape(safe_filename)}/tsv" class="btn">Download TSV</a>
    <a href="/export/raw/{escape(safe_filename)}/psv" class="btn">Download PSV</a>
    <a href="/export/raw/{escape(safe_filename)}/html" class="btn">Download HTML</a>
</div>
<div class="card">
    {table_html}
</div>
<a href="/dashboard/raw-scrape" class="btn" style="margin-top:1rem;">Back to Raw Scrape</a>
"""
    return _page_shell(f"Preview: {safe_filename}", body, nav_active="raw_scrape")


@router.get("/raw-file-preview")
def api_raw_file_preview(
    filename: str = Query(..., description="Raw file name to preview"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=500),
):
    """Preview rows from a raw file for the static dashboard."""
    try:
        rows = _load_raw_file_rows(filename)
    except FileNotFoundError:
        return {"ok": False, "error": f"Raw file not found: {filename}"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON in {filename}: {exc}"}

    total = len(rows)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_items = rows[start_idx:end_idx]

    return {
        "ok": True,
        "filename": Path(filename).name,
        "total": total,
        "page": page,
        "limit": limit,
        "preview_count": len(paginated_items),
        "items": paginated_items,
    }


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
    <a href="/export/products/psv" class="btn">PSV</a>
    <a href="/export/products/html" class="btn">HTML</a>
  </div>
  <div class="card">
    <h2>Jobs</h2>
    <a href="/export/jobs/csv" class="btn">CSV</a>
    <a href="/export/jobs/tsv" class="btn">TSV</a>
    <a href="/export/jobs/psv" class="btn">PSV</a>
    <a href="/export/jobs/html" class="btn">HTML</a>
  </div>
</div>
<h2 style="margin-top:2rem;">Load Raw Data to PostgreSQL</h2>
<div class="card" style="margin-top:1rem;">
  <p class="meta">Load scraped JSON data from data/raw into the PostgreSQL database.</p>
  <a href="/dashboard/load-to-db" class="btn">Load to DB</a>
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


@router.get("/raw-scrape", response_class=HTMLResponse)
def dashboard_raw_scrape():
        """Render manual raw scrape form."""
        body = """
<h1>Manual Raw Scrape</h1>
<p class="meta">Run one spider and save only raw scraped data to a JSON file in data/raw.</p>
<form method="post" action="/dashboard/raw-scrape" style="display:grid;gap:1rem;max-width:700px;background:#fff;padding:1rem;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);">
    <label>
        Spider
        <select name="spider" style="display:block;margin-top:.35rem;padding:.45rem;width:100%;">
            <option value="products">products</option>
            <option value="jobs">jobs</option>
        </select>
    </label>
    <label>
        URL (optional)
        <input type="url" name="url" placeholder="https://example.com" style="display:block;margin-top:.35rem;padding:.45rem;width:100%;" />
    </label>
    <label style="display:flex;align-items:center;gap:.5rem;">
        <input type="checkbox" name="sitemap" value="true">
        Use sitemap discovery
    </label>
    <label>
        Sitemap URL (optional)
        <input type="url" name="sitemap_url" placeholder="https://example.com/sitemap.xml" style="display:block;margin-top:.35rem;padding:.45rem;width:100%;" />
    </label>
    <label>
        Preview Items
        <input type="number" name="preview_limit" min="1" max="100" value="10" style="display:block;margin-top:.35rem;padding:.45rem;width:140px;" />
    </label>
    <button type="submit" style="padding:.6rem 1rem;background:#0d6efd;color:#fff;border:none;border-radius:4px;cursor:pointer;width:max-content;">Run Raw Scrape</button>
</form>
"""
        return _page_shell("Manual Raw Scrape", body, nav_active="raw_scrape")


@router.post("/raw-scrape", response_class=HTMLResponse)
def dashboard_raw_scrape_run(
        spider: str = Form(...),
        url: str | None = Form(default=None),
    sitemap: bool = Form(default=False),
    sitemap_url: str | None = Form(default=None),
        preview_limit: int = Form(default=10),
):
        """Run a manual scrape and show saved JSON output details in UI."""
        if spider not in {"products", "jobs"}:
                body = "<h1>Manual Raw Scrape</h1><p class='meta'>Invalid spider selected.</p>"
                return _page_shell("Manual Raw Scrape", body, nav_active="raw_scrape")

        normalized_url = (url or "").strip() or None
        normalized_sitemap_url = (sitemap_url or "").strip() or None
        safe_preview_limit = max(1, min(preview_limit, 100))
        result = _run_raw_scrape(
                spider=spider,
                url=normalized_url,
            use_sitemap=sitemap,
            sitemap_urls=[normalized_sitemap_url] if normalized_sitemap_url else None,
                max_items=safe_preview_limit,
        )

        if not result["ok"]:
                body = f"""
<h1>Manual Raw Scrape</h1>
<p class="meta" style="color:#b42318;">Scrape failed: {escape(result['error'])}</p>
<a href="/dashboard/raw-scrape" class="btn">Try again</a>
"""
                return _page_shell("Manual Raw Scrape", body, nav_active="raw_scrape")

        # Render preview as table with images and clickable links
        preview_table = _render_raw_preview_table(result["preview"])

        # Get the filename for export links
        file_name = Path(result["file"]).name
        item_type = "job" if "job" in spider.lower() else "product"

        body = f"""
<h1>Manual Raw Scrape</h1>
<p class="meta" style="color:#027a48;">Saved {result['count']} raw items to data/raw.</p>
<div class="card" style="margin-bottom:1rem;">
    <h2>Saved File</h2>
    <p>{escape(result['file'])}</p>
    <p class="meta">Spider: {escape(spider)}{f" | URL: {escape(normalized_url)}" if normalized_url else ""}{" | Sitemap: enabled" if sitemap else ""}{f" | Sitemap URL: {escape(normalized_sitemap_url)}" if normalized_sitemap_url else ""}</p>
</div>

<div class="card" style="margin-bottom:1rem;">
    <h2>Export Options</h2>
    <div class="export-btns">
        <a href="/export/raw/{escape(file_name)}/csv" class="btn">CSV</a>
        <a href="/export/raw/{escape(file_name)}/tsv" class="btn">TSV</a>
        <a href="/export/raw/{escape(file_name)}/psv" class="btn">PSV</a>
        <a href="/export/raw/{escape(file_name)}/html" class="btn">HTML</a>
    </div>
    <form method="post" action="/dashboard/load-to-db" style="display:inline;">
        <input type="hidden" name="filename" value="{escape(file_name)}">
        <input type="hidden" name="item_type" value="{item_type}">
        <button type="submit" class="btn btn-success">Load to PostgreSQL</button>
    </form>
</div>

<div class="card">
    <h2>Preview (first {safe_preview_limit})</h2>
    {preview_table}
</div>
<a href="/dashboard/raw-scrape" class="btn">Run another raw scrape</a>
"""
        return _page_shell("Manual Raw Scrape", body, nav_active="raw_scrape")


@router.get("/load-to-db", response_class=HTMLResponse)
def dashboard_load_to_db():
    """Render the Load to DB page with available raw JSON files."""
    files_html = ""
    raw_dir = RAW_OUTPUT_DIR
    if raw_dir.exists():
        json_files = sorted(raw_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if json_files:
            for f in json_files:
                item_type = "job" if "job" in f.name.lower() else "product"
                size_kb = f.stat().st_size / 1024
                files_html += f"""
<div class="card" style="margin-bottom:1rem;">
    <h2>{escape(f.name)}</h2>
    <p class="meta">Type: {item_type} | Size: {size_kb:.1f} KB</p>
    <form method="post" action="/dashboard/load-to-db" style="display:inline;">
        <input type="hidden" name="filename" value="{escape(f.name)}">
        <input type="hidden" name="item_type" value="{item_type}">
        <button type="submit" class="btn" style="border:none;cursor:pointer;">Load to PostgreSQL</button>
    </form>
</div>
"""
        else:
            files_html = '<p class="meta">No raw JSON files found in data/raw.</p>'
    else:
        files_html = '<p class="meta">data/raw directory does not exist. Run a raw scrape first.</p>'

    body = f"""
<h1>Load Raw Data to PostgreSQL</h1>
<p class="meta">Select a raw JSON file to load into the PostgreSQL database.</p>
{files_html}
<a href="/dashboard/" class="btn">Back to Dashboard</a>
"""
    return _page_shell("Load to DB", body, nav_active="home")


@router.post("/load-to-db", response_class=HTMLResponse)
def dashboard_load_to_db_run(
    filename: str = Form(...),
    item_type: str = Form(...),
):
    """Load selected raw JSON file into PostgreSQL."""
    import requests

    # Call the export API endpoint to load data
    try:
        # Use internal API call to load data
        from api.routes.export import load_to_postgresql, _clean_record, _upsert_products, _upsert_jobs, RAW_DATA_DIR
        from data_models import SessionLocal

        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            body = f"""
<h1>Load to DB</h1>
<p class="meta" style="color:#b42318;">File not found: {escape(filename)}</p>
<a href="/dashboard/load-to-db" class="btn">Try again</a>
"""
            return _page_shell("Load to DB", body, nav_active="home")

        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_records = []
        for rec in data:
            url = rec.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_records.append(_clean_record(rec, item_type))

        session = SessionLocal()
        try:
            if item_type == "product":
                count = _upsert_products(session, unique_records)
            else:
                count = _upsert_jobs(session, unique_records)

            body = f"""
<h1>Load to DB</h1>
<p class="meta" style="color:#027a48;">Successfully loaded {count} {item_type}(s) into PostgreSQL.</p>
<div class="card">
    <h2>Details</h2>
    <p>File: {escape(filename)}</p>
    <p>Type: {item_type}</p>
    <p>Records loaded: {count}</p>
</div>
<a href="/dashboard/load-to-db" class="btn">Load another file</a>
<a href="/dashboard/" class="btn">Back to Dashboard</a>
"""
            return _page_shell("Load to DB", body, nav_active="home")
        except Exception as e:
            session.rollback()
            body = f"""
<h1>Load to DB</h1>
<p class="meta" style="color:#b42318;">Database error: {escape(str(e))}</p>
<a href="/dashboard/load-to-db" class="btn">Try again</a>
"""
            return _page_shell("Load to DB", body, nav_active="home")
        finally:
            session.close()

    except Exception as e:
        body = f"""
<h1>Load to DB</h1>
<p class="meta" style="color:#b42318;">Error: {escape(str(e))}</p>
<a href="/dashboard/load-to-db" class="btn">Try again</a>
"""
        return _page_shell("Load to DB", body, nav_active="home")
