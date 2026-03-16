# Adding a New Crawler

This guide walks you through adding a new spider to the platform.

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

Add the spider to the worker registry in `infrastructure/workers/worker.py`:

```python
SPIDER_REGISTRY["news"] = "crawlers.news.news_spider.NewsSpider"
```

And add the module to `SPIDER_MODULES` in `crawlers/settings.py`:

```python
SPIDER_MODULES = ["crawlers.ecommerce", "crawlers.jobs", "crawlers.news"]
```

## 4. Create a data model (if needed)

Add a new SQLAlchemy model in `data_models/` and update `pipelines/load/db_loader.py` to handle the new item type.

## 5. Write tests

Add a test file at `tests/test_crawlers/test_news_spider.py` following the existing patterns.

## 6. Test it

```bash
# Run directly
python -m scripts.run_spider news

# Or via a worker
echo '{"spider": "news"}' | redis-cli -x rpush scraping:jobs
python -m infrastructure.workers.worker
```
