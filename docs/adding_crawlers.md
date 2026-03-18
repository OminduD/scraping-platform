# Adding a New Crawler

This guide walks you through adding a new spider to the platform.

## Available Spiders

Currently supported spiders:
- `products` — E-commerce product scraper
- `jobs` — Job listing scraper

## 1. Create the spider module

Create a new directory under `crawlers/` for your domain, e.g. `crawlers/news/`:

```bash
mkdir -p crawlers/news
touch crawlers/news/__init__.py
```

## 2. Write the spider

Create `crawlers/news/news_spider.py`:

```python
from __future__ import annotations
from typing import Any, Generator
import scrapy
from crawlers.base import BaseSpider

class NewsSpider(BaseSpider):
    name = "news"
    allowed_domains = ["example-news.com"]
    start_urls = ["https://example-news.com/latest"]

    # Optional: Configure custom feeds for raw JSON output
    custom_settings = {
        "FEEDS": {
            "data/processed/news.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
            }
        }
    }

    def parse(self, response: scrapy.http.Response, **kwargs) -> Generator:
        self._record_success(response.url)

        for article in response.css("article.post"):
            item = {
                "title": article.css("h2::text").get("").strip(),
                "url": response.urljoin(article.css("a::attr(href)").get("")),
                "source": "example-news.com",
            }
            self._record_item("news_article")
            yield item
```

## 3. Register the spider

Add the spider to `scripts/run_spider.py`:

```python
SPIDERS = {
    "products": "crawlers.ecommerce.product_spider.ProductSpider",
    "jobs": "crawlers.jobs.job_spider.JobSpider",
    "news": "crawlers.news.news_spider.NewsSpider",
}
```

And add the module to `SPIDER_MODULES` in `crawlers/settings.py`:

```python
SPIDER_MODULES = ["crawlers.ecommerce", "crawlers.jobs", "crawlers.news"]
```

## 4. Add export pipeline support (optional)

If you want automatic TSV/HTML export on spider close:

**In `pipelines/export/tsv_exporter.py`:**

```python
SPIDER_OUTPUT_FILES = {
    "products": "products.tsv",
    "jobs": "jobs.tsv",
    "news": "news.tsv",
}

NEWS_FIELDS = ["title", "url", "source", "published_at"]

SPIDER_FIELDS = {
    "products": PRODUCT_FIELDS,
    "jobs": JOB_FIELDS,
    "news": NEWS_FIELDS,
}
```

**In `pipelines/export/html_exporter.py`:**

```python
SPIDER_OUTPUT_FILES = {
    "products": "products.html",
    "jobs": "jobs.html",
    "news": "news.html",
}
```

## 5. Create a data model (if database storage needed)

Add a new SQLAlchemy model in `data_models/` and update `pipelines/load/db_loader.py` to handle the new item type:

```python
def process_item(self, item: dict[str, Any], spider) -> dict[str, Any]:
    # ...
    if spider_name == "products":
        self._upsert_product(item)
    elif spider_name == "jobs":
        self._upsert_job(item)
    elif spider_name == "news":
        self._upsert_news(item)
```

## 6. Add to web dashboard (optional)

To enable raw scraping from the web UI, update `static/raw-scrape.html`:

```html
<select id="spider" name="spider" required>
  <option value="products">Products</option>
  <option value="jobs">Jobs</option>
  <option value="news">News</option>
</select>
```

And update validation in `api/routes/dashboard.py`:

```python
if spider not in {"products", "jobs", "news"}:
    return {"ok": False, "error": "Invalid spider selected."}
```

## 7. Write tests

Add a test file at `tests/test_crawlers/test_news_spider.py` following the existing patterns.

## 8. Test it

### Test directly

```bash
# Run with default URLs
python -m scripts.run_spider news

# Run with custom URL
python -m scripts.run_spider news --url https://example-news.com/tech

# Save raw JSON output
python -m scripts.run_spider news --output-json data/raw/news.json
```

### Test via web dashboard

1. Start the server: `uvicorn api.main:app --reload`
2. Visit http://localhost:8000/static/raw-scrape.html
3. Select your spider and run

### Test via worker queue

```bash
# Enqueue a job
echo '{"spider": "news"}' | redis-cli -x rpush scraping:jobs

# Start a worker
python -m infrastructure.workers.worker
```

## Data Flow

```
Spider → Raw JSON (data/raw/) → Load to DB → PostgreSQL
                ↓
         Export (TSV/HTML) → data/processed/
```

- **Raw scraping** saves to `data/raw/` without database processing
- **Pipeline processing** automatically exports to `data/processed/` as TSV/HTML
- **Database loading** uses upsert (INSERT ... ON CONFLICT UPDATE) to deduplicate by URL
