# Scraping Platform

A scalable, distributed web scraping platform for collecting public website data, processing it through ETL pipelines, storing it in PostgreSQL, and exposing it via a REST API and interactive web dashboard.

Built with **Python 3.14**, **Scrapy**, **FastAPI**, **Redis**, **PostgreSQL**, **Docker**, and **Prometheus/Grafana** monitoring.

## Architecture

```
┌─────────────┐     ┌───────────┐     ┌──────────────┐
│  Scheduler   │────▶│   Redis    │◀────│   Workers    │
│  (cron/API)  │     │  (Queue)   │     │  (N replicas)│
└─────────────┘     └───────────┘     └──────┬───────┘
                                              │
                                              ▼
                                     ┌────────────────┐
                                     │    Crawlers     │
                                     │ (Scrapy + PW)  │
                                     └────────┬───────┘
                                              │
                            ┌─────────────────┼─────────────────┐
                            ▼                 ▼                 ▼
                     ┌────────────┐   ┌────────────┐   ┌────────────┐
                     │  Extract   │──▶│ Transform  │──▶│   Load     │
                     │ (HTML→text)│   │ (clean/    │   │ (PostgreSQL│
                     └────────────┘   │  dedup)    │   │  upsert)   │
                                      └────────────┘   └────────────┘
                                                              │
                                                              ▼
                                                     ┌────────────────┐
                                                     │  FastAPI       │
                                                     │  REST API +    │
                                                     │  Web Dashboard │
                                                     └────────┬───────┘
                                                              │
                                                     ┌────────┼───────┐
                                                     ▼        ▼       ▼
                                              Dashboard  Export   Metrics
                                              (HTML/JS)  (CSV/TSV) (Prom)
```

**Scheduler** enqueues crawl jobs into **Redis**. **Workers** (horizontally scalable) pop jobs and execute **Scrapy spiders**. Scraped data flows through a three-stage **ETL pipeline** (extract HTML → transform/clean → load into PostgreSQL). The **FastAPI** service serves data via REST API and an interactive web dashboard with export capabilities. **Prometheus** collects metrics and **Grafana** visualizes them.

## Project Structure

```
scraping-platform/
├── crawlers/               # Scrapy spiders
│   ├── base/               #   Base spider with metrics & logging
│   ├── ecommerce/          #   Product listing spider
│   └── jobs/               #   Job listing spider
├── pipelines/              # ETL pipeline stages
│   ├── extract/            #   HTML parsing & cleanup
│   ├── transform/          #   Cleaning, dedup, normalization
│   ├── load/               #   PostgreSQL upsert
│   └── export/             #   TSV/HTML exporters
├── api/                    # FastAPI REST service
│   ├── routes/             #   REST & dashboard endpoints
│   ├── services/           #   Business logic
│   └── schemas/            #   Pydantic response models
├── static/                 # Web dashboard (HTML/CSS/JS)
│   ├── index.html          #   Main dashboard
│   ├── raw-scrape.html     #   Manual scrape interface
│   ├── load-to-db.html     #   Database loader
│   ├── css/                #   Stylesheets
│   └── js/                 #   JavaScript utilities
├── data_models/            # SQLAlchemy ORM models
├── infrastructure/
│   ├── scheduler/          # Redis job enqueuer
│   ├── workers/            # Distributed worker loop
│   └── storage/            # Raw/processed file storage
├── data/                   # Data storage
│   ├── raw/                #   Raw JSON outputs
│   ├── processed/          #   Processed exports
│   └── images/             #   Downloaded images
├── configs/                # YAML configs & settings
├── scripts/                # CLI utilities
├── docker/                 # Dockerfiles
├── dashboards/             # Grafana dashboard JSON
├── tests/                  # pytest test suite
├── docs/                   # Documentation
├── notebooks/              # Jupyter exploration notebooks
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── Makefile
└── .env.example
```

## Quick Start

### Option A — Docker (recommended)

```bash
# Clone and start all services
cp .env.example .env
make up

# Web Dashboard at http://localhost:8000
# API documentation at http://localhost:8000/docs
# Grafana at http://localhost:3000 (admin/admin)
```

### Option B — Local development

```bash
# Prerequisites: Python 3.14+, PostgreSQL, Redis running locally

# Install dependencies
make dev

# Copy and edit environment variables
cp .env.example .env

# Create database tables
python scripts/init_db.py

# Seed sample data
python scripts/seed_db.py

# Start the API
make api

# Run a crawler
make crawl SPIDER=products

# Access the web dashboard at http://localhost:8000
```

## Running Crawlers

### Directly

```bash
python -m scripts.run_spider products
python -m scripts.run_spider jobs
python -m scripts.run_spider products --download-images
```

By default, crawlers store the product `image_url` only. Use `--download-images` when you also want to download image files.

### Via worker queue

```bash
# Enqueue jobs from a manifest
python -m infrastructure.scheduler.scheduler scripts/sample_manifest.json

# Start workers (they'll pick up queued jobs automatically)
python -m infrastructure.workers.worker
```

### Via Docker

```bash
# Run the crawler profile
docker compose --profile crawl up crawler
```

## Web Dashboard

Access the interactive web dashboard at `http://localhost:8000`:

- **Home** — View statistics, recent products/jobs, export to CSV/TSV/PSV
- **Raw Scrape** — Run manual scrapes without database processing, save raw JSON to `data/raw/`
- **Load to DB** — Load raw JSON files into PostgreSQL database

Features:
- Images displayed inline using URLs
- Clickable hyperlinks for product/job URLs
- Export buttons for CSV, TSV, PSV, HTML formats
- Real-time scrape preview with table rendering

## API Endpoints

### REST API (v1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/products/` | List products (paginated, filterable) |
| `GET` | `/api/v1/products/{id}` | Get single product |
| `GET` | `/api/v1/jobs/` | List job listings (paginated, filterable) |
| `GET` | `/api/v1/jobs/{id}` | Get single job listing |
| `GET` | `/api/v1/analytics/` | Aggregate statistics |
| `POST` | `/api/v1/raw-scrape` | Run manual scrape, return JSON |
| `GET` | `/api/v1/raw-files` | List raw JSON files |
| `GET` | `/metrics` | Prometheus metrics |

### Export Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/export/products/{format}` | Export all products (csv/tsv/psv/html) |
| `GET` | `/export/jobs/{format}` | Export all jobs (csv/tsv/psv/html) |
| `GET` | `/export/raw/{filename}/{format}` | Export raw file (csv/tsv/psv/html) |
| `POST` | `/export/load-to-db` | Load raw JSON to PostgreSQL |

### Legacy Endpoints

Legacy endpoints without `/api/v1` prefix are maintained for backwards compatibility.

Full API docs with interactive Swagger UI at `/docs`.

See [docs/api.md](docs/api.md) for detailed documentation.

## Adding a New Crawler

1. Create a spider module under `crawlers/your_domain/`
2. Inherit from `BaseSpider` for built-in metrics and logging
3. Register it in the worker registry and Scrapy settings
4. Optionally add a data model and update the load pipeline

See [docs/adding_crawlers.md](docs/adding_crawlers.md) for a full walkthrough.

## Monitoring

Prometheus scrapes the `/metrics` endpoint on the API service. Pre-configured metrics:

- `scrape_success_total` — successful page scrapes (by spider)
- `scrape_failure_total` — failed page scrapes (by spider)
- `scrape_duration_seconds` — histogram of scrape times
- `items_scraped_total` — items extracted (by spider and type)

A Grafana dashboard is included at `dashboards/scraping_overview.json` and auto-provisioned when using Docker Compose.

## Testing

```bash
make test
```

Tests use an in-memory SQLite database and cover:
- Spider parsing logic
- ETL pipeline stages (extract, transform)
- API routes and responses

## Configuration

Configuration is loaded from environment variables (highest priority), with fallback to YAML files in `configs/`:

| File | Purpose |
|------|---------|
| `configs/crawler.yaml` | Crawl delay, retries, concurrency |
| `configs/database.yaml` | Database connection settings |
| `configs/logging.yaml` | Structured logging configuration |

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `REDIS_HOST` | `localhost` | Redis host |
| `CRAWL_DELAY` | `1.5` | Seconds between requests |
| `CONCURRENT_REQUESTS` | `8` | Max concurrent requests |

See `.env.example` for the full list.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Scraping | Scrapy + Playwright |
| Data Processing | Pandas |
| Database | PostgreSQL + SQLAlchemy |
| Queue | Redis |
| API | FastAPI |
| Containers | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |
| Testing | pytest |

## License

MIT — see [LICENSE](LICENSE).
