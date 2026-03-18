# Changelog

## [Unreleased] - 2026-03-18

### Added

#### Web Dashboard
- **Static HTML Dashboard** — New interactive web UI at `/static/`
  - `index.html` — Main dashboard with statistics and data tables
  - `raw-scrape.html` — Manual scrape interface
  - `load-to-db.html` — Database loader for raw JSON files
  - `css/style.css` — Shared styling
  - `js/dashboard.js` — JavaScript utilities for table rendering

#### Export Functionality
- **Multiple Export Formats** — CSV, TSV, PSV, HTML
  - `/export/products/{format}` — Export all products
  - `/export/jobs/{format}` — Export all jobs
  - `/export/raw/{filename}/{format}` — Export raw JSON files
- **Export Buttons** — Added to all dashboard pages
- **Auto-export Pipelines** — TSV and HTML files auto-generated on spider close

#### API Endpoints
- `POST /api/v1/raw-scrape` — JSON API for manual scrapes
- `GET /api/v1/raw-files` — List raw JSON files
- `POST /export/load-to-db` — Load raw JSON to PostgreSQL
- **API Versioning** — All endpoints now prefixed with `/api/v1/`
- **Legacy Routes** — Backwards compatibility maintained for old endpoints

#### Features
- **Inline Image Display** — Product images shown in tables using `image_url`
- **Clickable URLs** — All URLs rendered as hyperlinks with `target="_blank"`
- **Raw Data Storage** — All raw scrapes save to `data/raw/`
- **Static File Serving** — FastAPI serves static files from `/static/`
- **Root Redirect** — `/` redirects to `/static/index.html`

#### Documentation
- **web-dashboard.md** — Complete guide to the web dashboard
- **Updated README.md** — Added web dashboard section, updated architecture
- **Updated api.md** — All new API endpoints documented
- **Updated architecture.md** — Added data flow diagrams, storage structure
- **Updated adding_crawlers.md** — Guide for adding new spiders with export support

### Changed
- **Python Version** — Updated from 3.11 to 3.14
- **Data Flow** — Raw scrapes now save to `data/raw/` instead of `data/processed/`
- **Dashboard Rendering** — Switched from server-side HTML generation to static files + JSON API
- **Export Architecture** — Separated database exports from raw file exports

### Removed
- **Anix Spider** — Removed `crawlers/ecommerce/anix_spider.py`
- **Anix References** — Cleaned up from:
  - `scripts/run_spider.py`
  - `pipelines/export/tsv_exporter.py`
  - `pipelines/export/html_exporter.py`
  - `pipelines/load/db_loader.py`
  - `api/routes/dashboard.py`
- **Server-side HTML Templates** — Dashboard no longer uses inline HTML generation

### Fixed
- **Missing Dependency** — Added `python-multipart` for form data handling
- **Docker Volumes** — Added static and data directory mounts in `docker-compose.yml`

## Migration Guide

### For Users

**Old Dashboard:**
```
http://localhost:8000/dashboard/
```

**New Dashboard:**
```
http://localhost:8000/
```

**Old API Endpoints:**
```
GET /products/
GET /jobs/
GET /analytics/
```

**New API Endpoints (preferred):**
```
GET /api/v1/products/
GET /api/v1/jobs/
GET /api/v1/analytics/
```

*(Legacy endpoints still work)*

### For Developers

**Raw Scrapes:**

Old behavior:
- Scraped data went to `data/processed/` with pipeline processing

New behavior:
- Manual raw scrapes go to `data/raw/` without processing
- Pipeline scrapes still go to `data/processed/`

**Adding Export Support:**

When adding a new spider, update these files:
1. `scripts/run_spider.py` — Add spider to SPIDERS dict
2. `pipelines/export/tsv_exporter.py` — Add to SPIDER_OUTPUT_FILES and SPIDER_FIELDS
3. `pipelines/export/html_exporter.py` — Add to SPIDER_OUTPUT_FILES
4. `static/raw-scrape.html` — Add to spider dropdown (optional)
5. `api/routes/dashboard.py` — Add to validation (optional)

## Breaking Changes

### Removed Spiders
- **anix** spider has been removed
- Any scripts or configurations using `spider=anix` will fail

### Database Schema
No breaking changes to database schema.

### API
No breaking changes — legacy endpoints maintained.

## Upgrade Instructions

1. Pull latest code
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Restart the API:
   ```bash
   uvicorn api.main:app --reload
   ```
4. Access new dashboard at http://localhost:8000

## Dependencies Added
- `python-multipart` — For multipart form data handling in FastAPI

## File Structure Changes

**New Directories:**
```
static/
├── css/
│   └── style.css
├── js/
│   └── dashboard.js
├── index.html
├── raw-scrape.html
└── load-to-db.html

docs/
└── web-dashboard.md (new)
```

**Removed Files:**
- `crawlers/ecommerce/anix_spider.py`
