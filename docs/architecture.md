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
                                      └────────────┘   └────────────┘
                                                              │
                                                              ▼
                                                     ┌────────────────┐
                                                     │   PostgreSQL   │
                                                     └────────┬───────┘
                                                              │
                                                              ▼
                                                     ┌────────────────┐
                                                     │  FastAPI (REST)│
                                                     │  /products     │
                                                     │  /jobs         │
                                                     │  /analytics    │
                                                     └────────────────┘
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
| **Load** | Upsert records into PostgreSQL |
| **API** | FastAPI service exposing products, jobs, and analytics |
| **Monitoring** | Prometheus metrics + Grafana dashboards |
