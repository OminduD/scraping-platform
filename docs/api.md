# API Documentation

The scraping platform exposes a REST API built with FastAPI, along with an interactive web dashboard.

**Base URL:** `http://localhost:8000`

## Web Dashboard

Access the web UI at `http://localhost:8000`:

- **Dashboard** (`/static/index.html`) — View statistics, recent items, export data
- **Raw Scrape** (`/static/raw-scrape.html`) — Run manual scrapes without DB processing
- **Load to DB** (`/static/load-to-db.html`) — Load raw JSON files into PostgreSQL

## REST API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{"status": "ok"}
```

### Products

#### List products

```
GET /api/v1/products/?skip=0&limit=50&source=books.toscrape.com
```

| Parameter | Type   | Default | Description              |
|-----------|--------|---------|--------------------------|
| `skip`    | int    | 0       | Pagination offset        |
| `limit`   | int    | 50      | Page size (max 500)      |
| `source`  | string | —       | Filter by source domain  |

Response:
```json
{
  "total": 1000,
  "items": [
    {
      "id": 1,
      "title": "A Light in the Attic",
      "price": 51.77,
      "currency": "GBP",
      "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
      "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
      "source": "books.toscrape.com",
      "created_at": "2026-03-18T10:30:00Z"
    }
  ]
}
```

#### Get single product

```
GET /api/v1/products/{product_id}
```

### Jobs

#### List jobs

```
GET /api/v1/jobs/?skip=0&limit=50&source=realpython.github.io
```

Parameters identical to products.

Response:
```json
{
  "total": 500,
  "items": [
    {
      "id": 1,
      "title": "Software Engineer",
      "company": "Acme Corp",
      "location": "Remote",
      "url": "https://realpython.github.io/fake-jobs/jobs/senior-python-developer-job.html",
      "source": "realpython.github.io/fake-jobs",
      "posted_at": "2024-01-15",
      "created_at": "2026-03-18T10:30:00Z"
    }
  ]
}
```

#### Get single job

```
GET /api/v1/jobs/{job_id}
```

### Analytics

```
GET /api/v1/analytics/
```

Response:
```json
{
  "total_products": 1000,
  "total_jobs": 500,
  "products_by_source": [
    {"source": "books.toscrape.com", "count": 1000}
  ],
  "jobs_by_source": [
    {"source": "realpython.github.io/fake-jobs", "count": 500}
  ],
  "avg_product_price": 35.42
}
```

### Dashboard API

#### Run raw scrape

```
POST /api/v1/raw-scrape
Content-Type: multipart/form-data

spider=products&url=https://example.com&preview_limit=10
```

Response:
```json
{
  "ok": true,
  "file": "data/raw/products_raw_20260318T103000Z.json",
  "count": 50,
  "preview": [
    {
      "title": "Product Name",
      "price": "$29.99",
      "url": "https://example.com/product",
      "image_url": "https://example.com/image.jpg"
    }
  ]
}
```

#### List raw files

```
GET /api/v1/raw-files
```

Response:
```json
{
  "files": [
    {
      "name": "products_raw_20260318T103000Z.json",
      "size": 45678,
      "modified": "2026-03-18T10:30:00Z"
    }
  ]
}
```

### Export Endpoints

#### Export database data

```
GET /export/products/csv
GET /export/products/tsv
GET /export/products/psv
GET /export/products/html

GET /export/jobs/csv
GET /export/jobs/tsv
GET /export/jobs/psv
GET /export/jobs/html
```

Downloads the entire product or job dataset in the specified format.

| Format | Description | MIME Type |
|--------|-------------|-----------|
| `csv` | Comma-separated values | `text/csv` |
| `tsv` | Tab-separated values | `text/tab-separated-values` |
| `psv` | Pipe-separated values | `text/plain` |
| `html` | Styled HTML table | `text/html` |

#### Export raw files

```
GET /export/raw/{filename}/csv
GET /export/raw/{filename}/tsv
GET /export/raw/{filename}/psv
GET /export/raw/{filename}/html
```

Converts a raw JSON file from `data/raw/` to the specified format.

#### Load to database

```
POST /export/load-to-db?filename=products_raw_20260318T103000Z.json&item_type=product
```

Loads a raw JSON file into PostgreSQL database with deduplication and normalization.

Response:
```json
{
  "ok": true,
  "message": "Successfully loaded 50 product(s) into PostgreSQL",
  "loaded": 50,
  "file": "products_raw_20260318T103000Z.json"
}
```

### Prometheus Metrics

```
GET /metrics
```

Returns Prometheus-format metrics including:
- `scrape_success_total` — Successful page scrapes by spider
- `scrape_failure_total` — Failed page scrapes by spider
- `scrape_duration_seconds` — Histogram of scrape times
- `items_scraped_total` — Items extracted by spider and type

## Legacy Endpoints

For backwards compatibility, endpoints without `/api/v1` prefix are also available:

- `GET /products/` → `GET /api/v1/products/`
- `GET /jobs/` → `GET /api/v1/jobs/`
- `GET /analytics/` → `GET /api/v1/analytics/`

## Interactive Docs

FastAPI provides auto-generated interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
