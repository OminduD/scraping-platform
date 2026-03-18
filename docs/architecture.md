# Architecture

## High-Level Overview

```
┌─────────────┐     ┌───────────┐     ┌──────────────┐
│  Scheduler   │────▶│   Redis    │◀────│   Workers    │
│  (cron/API)  │     │  (Queue)   │     │  (N replicas)│
└─────────────┘     └───────────┘     └──────┬───────┘
                                              │
                                              ▼
                                     ┌────────────────┐
                                     │    Crawlers     │
                                     │ (Scrapy/PW)    │
                                     └────────┬───────┘
                                              │
                            ┌─────────────────┼─────────────────┐
                            ▼                 ▼                 ▼
                     ┌────────────┐   ┌────────────┐   ┌────────────┐
                     │  Extract   │──▶│ Transform  │──▶│   Load     │
                     │ (HTML→text)│   │ (clean/    │   │ (PostgreSQL│
                     └────────────┘   │  dedup)    │   │  upsert)   │
                                      └────────────┘   └─────┬──────┘
                                              │               │
                                              ▼               ▼
                                      ┌────────────┐   ┌────────────┐
                                      │   Export   │   │ PostgreSQL │
                                      │ (TSV/HTML) │   └─────┬──────┘
                                      └────────────┘         │
                                                             ▼
                                                    ┌────────────────┐
                                                    │  FastAPI       │
                                                    │  REST + Web UI │
                                                    └────────┬───────┘
                                                             │
                                                    ┌────────┼────────┐
                                                    ▼        ▼        ▼
                                              Dashboard  Export   Metrics
                                              (Static)   (API)    (Prom)
```

## Component Responsibilities

| Component | Description |
|-----------|-------------|
| **Scheduler** | Enqueues crawl jobs (spider name + start URL) into Redis |
| **Redis** | Message queue for distributing crawl work |
| **Workers** | Long-running processes that pop jobs and execute spiders |
| **Crawlers** | Scrapy spiders (+ optional Playwright) that fetch & parse pages |
| **Extract** | Strip HTML, convert to plain text |
| **Transform** | Clean fields, deduplicate, normalize prices |
| **Load** | Upsert records into PostgreSQL using INSERT ... ON CONFLICT |
| **Export** | Generate TSV/HTML files on spider close |
| **API** | FastAPI service exposing REST API and web dashboard |
| **Web Dashboard** | Static HTML/CSS/JS interface for manual scraping and data export |
| **Monitoring** | Prometheus metrics + Grafana dashboards |

## Data Flow

### Pipeline Mode (Full ETL)

```
Spider → Extract → Transform → Load → PostgreSQL → Export (TSV/HTML)
                                            ↓
                                      FastAPI REST
```

1. Crawler extracts raw data from websites
2. Extract pipeline removes HTML tags and cleans text
3. Transform pipeline deduplicates, parses prices, normalizes fields
4. Load pipeline upserts to PostgreSQL (INSERT ... ON CONFLICT UPDATE)
5. Export pipeline generates TSV/HTML reports
6. FastAPI serves data via REST endpoints

### Raw Mode (No Database)

```
Spider → Raw JSON (data/raw/) → Manual Load → PostgreSQL
                    ↓
              Export (CSV/TSV/PSV/HTML)
```

1. Crawler saves raw JSON directly to `data/raw/`
2. Files can be exported to various formats without database
3. Manual loading available via web UI or CLI

## Web Dashboard

The platform includes a static web dashboard served by FastAPI:

### Pages

- **Home** (`/static/index.html`)
  - View total counts and statistics
  - Display recent products/jobs in tables
  - Export entire database (CSV, TSV, PSV, HTML)

- **Raw Scrape** (`/static/raw-scrape.html`)
  - Run spiders manually via web form
  - Save raw JSON to `data/raw/`
  - Preview scraped items in a table
  - Images displayed inline, URLs clickable
  - Export raw data or load to PostgreSQL

- **Load to DB** (`/static/load-to-db.html`)
  - Browse raw JSON files
  - Load files into PostgreSQL with deduplication
  - Export raw files to CSV/TSV/PSV

### Features

- **No backend rendering** — Static HTML/CSS/JS with API calls
- **Inline image preview** — Display product images from URLs
- **Clickable links** — All URLs are hyperlinks
- **Multiple export formats** — CSV, TSV (tab), PSV (pipe), HTML
- **Real-time updates** — JSON API responses power dynamic content

## Storage

### File System

```
data/
├── raw/                # Raw JSON outputs (no processing)
│   └── products_raw_20260318T103000Z.json
├── processed/          # TSV/HTML exports from pipeline
│   ├── products.tsv
│   ├── products.html
│   ├── jobs.tsv
│   └── jobs.html
└── images/             # Downloaded product images (optional)
    └── full/
        └── abc123.jpg
```

### Database Schema

```sql
-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    title TEXT,
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    url TEXT UNIQUE NOT NULL,
    image_url TEXT,
    source VARCHAR(255),
    location VARCHAR(255),
    category VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Jobs table
CREATE TABLE job_listings (
    id SERIAL PRIMARY KEY,
    title TEXT,
    company VARCHAR(255),
    location VARCHAR(255),
    description TEXT,
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(255),
    posted_at DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

Unique constraint on `url` enables automatic deduplication via `ON CONFLICT DO UPDATE`.
