"""Job listing spider — scrapes job postings from an example jobs board.

This uses Playwright for JavaScript-rendered pages.  The spider demonstrates
how to integrate Playwright with Scrapy for dynamic content.

For demonstration purposes it targets a static mock.  Swap `start_urls`
and selectors for a real job board.
"""

from __future__ import annotations

from typing import Any, Generator

import scrapy
import structlog

from crawlers.base import BaseSpider

logger = structlog.get_logger(__name__)


class JobSpider(BaseSpider):
    """Crawl job listing pages and yield structured job items."""

    name = "jobs"
    allowed_domains = ["realpython.github.io"]
    start_urls = ["https://realpython.github.io/fake-jobs/"]

    custom_settings: dict[str, Any] = {
        "DOWNLOAD_DELAY": 2.0,
        "FEEDS": {
            "data/processed/jobs.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
            },
        },
    }

    def parse(self, response: scrapy.http.Response, **kwargs) -> Generator:
        self._record_success(response.url)

        for card in response.css("div.card-content"):
            item = {
                "title": card.css("h2.title::text").get("").strip(),
                "company": card.css("h3.company::text").get("").strip(),
                "location": card.css("p.location::text").get("").strip(),
                "posted_at": card.css("time::attr(datetime)").get(),
                "url": response.urljoin(
                    card.css("a[href*='jobs']::attr(href)").get("")
                ),
                "source": "realpython.github.io/fake-jobs",
            }
            self._record_item("job_listing")
            logger.debug("item.scraped", spider=self.name, title=item["title"])
            yield item
