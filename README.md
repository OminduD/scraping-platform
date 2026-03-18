# Scraping Platform

A scalable, distributed web scraping platform for collecting public website data, processing it through ETL pipelines, storing it in PostgreSQL, and exposing it via a REST API.

Built with **Python 3.11**, **Scrapy**, **FastAPI**, **Redis**, **PostgreSQL**, **Docker**, and **Prometheus/Grafana** monitoring.

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
                                                     │  FastAPI (REST)│
                                                     │  /products     │
                                                     │  /jobs         │
                                                     │  /analytics    │
                                                     └────────────────┘
                                                              │
                                                     ┌────────────────┐
                                                     │  Prometheus +  │
                                                     │   Grafana      │
                                                     └────────────────┘
```

**Scheduler** enqueues crawl jobs into **Redis**. **Workers** (horizontally scalable) pop jobs and execute **Scrapy spiders**. Scraped data flows through a three-stage **ETL pipeline** (extract HTML → transform/clean → load into PostgreSQL). The **FastAPI** service serves the data over REST. **Prometheus** collects metrics and **Grafana** visualizes them.

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
│   └── load/               #   PostgreSQL upsert
├── api/                    # FastAPI REST service
│   ├── routes/             #   Endpoint definitions
│   ├── services/           #   Business logic
│   └── schemas/            #   Pydantic response models
├── data_models/            # SQLAlchemy ORM models
├── infrastructure/
│   ├── scheduler/          # Redis job enqueuer
│   ├── workers/            # Distributed worker loop
│   └── storage/            # Raw/processed file storage
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

# API is available at http://localhost:8000
# Grafana at http://localhost:3000 (admin/admin)
# Swagger docs at http://localhost:8000/docs
```

### Option B — Local development

```bash
# Prerequisites: Python 3.11+, PostgreSQL, Redis running locally

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

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/products/` | List products (paginated, filterable) |
| `GET` | `/products/{id}` | Get single product |
| `GET` | `/jobs/` | List job listings (paginated, filterable) |
| `GET` | `/jobs/{id}` | Get single job listing |
| `GET` | `/analytics/` | Aggregate statistics |
| `GET` | `/metrics` | Prometheus metrics |

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
