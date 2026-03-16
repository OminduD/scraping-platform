# API Documentation

The scraping platform exposes a REST API built with FastAPI.

**Base URL:** `http://localhost:8000`

## Endpoints

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
GET /products/?skip=0&limit=50&source=books.toscrape.com
```

| Parameter | Type   | Default | Description              |
|-----------|--------|---------|--------------------------|
| `skip`    | int    | 0       | Pagination offset        |
| `limit`   | int    | 50      | Page size (max 500)      |
| `source`  | string | —       | Filter by source domain  |

#### Get single product

```
GET /products/{product_id}
```

### Jobs

#### List jobs

```
GET /jobs/?skip=0&limit=50&source=realpython.github.io
```

Parameters identical to products.

#### Get single job

```
GET /jobs/{job_id}
```

### Analytics

```
GET /analytics/
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

### Prometheus Metrics

```
GET /metrics
```

Returns Prometheus-format metrics including `scrape_success_total`, `scrape_failure_total`, `scrape_duration_seconds`, and `items_scraped_total`.

## Interactive Docs

FastAPI provides auto-generated interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
