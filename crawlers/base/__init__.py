"""Base spider with shared configuration, logging, and metrics."""

from __future__ import annotations

import time
from typing import Any

import scrapy
import structlog
from prometheus_client import Counter, Histogram

from configs import get_settings

logger = structlog.get_logger(__name__)

# ── Prometheus metrics ───────────────────────────────────────────────
SCRAPE_SUCCESS = Counter(
    "scrape_success_total",
    "Total successful page scrapes",
    ["spider"],
)
SCRAPE_FAILURE = Counter(
    "scrape_failure_total",
    "Total failed page scrapes",
    ["spider"],
)
SCRAPE_DURATION = Histogram(
    "scrape_duration_seconds",
    "Time spent scraping a single page",
    ["spider"],
)
ITEMS_SCRAPED = Counter(
    "items_scraped_total",
    "Total items extracted",
    ["spider", "item_type"],
)


class BaseSpider(scrapy.Spider):
    """Base spider that all project spiders should inherit from.

    Provides:
    - Automatically applied crawler settings (delay, retries, concurrency).
    - Structured logging on every request/response cycle.
    - Prometheus metric instrumentation.
    """

    name = "base"

    custom_settings: dict[str, Any] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        settings = get_settings().crawler
        self.custom_settings.setdefault("DOWNLOAD_DELAY", settings.crawl_delay)
        self.custom_settings.setdefault("RETRY_TIMES", settings.max_retries)
        self.custom_settings.setdefault("CONCURRENT_REQUESTS", settings.concurrent_requests)
        self._request_start_times: dict[str, float] = {}

    # ── Hooks ────────────────────────────────────────────────────────

    def start_requests(self):
        for url in self.start_urls:
            logger.info("crawl.start", spider=self.name, url=url)
            yield scrapy.Request(url, callback=self.parse, errback=self._on_error)

    def parse(self, response, **kwargs):
        """Subclasses must override this method."""
        raise NotImplementedError

    # ── Middleware-style hooks ────────────────────────────────────────

    def _record_start(self, url: str) -> None:
        self._request_start_times[url] = time.monotonic()

    def _record_success(self, url: str) -> None:
        SCRAPE_SUCCESS.labels(spider=self.name).inc()
        start = self._request_start_times.pop(url, None)
        if start is not None:
            SCRAPE_DURATION.labels(spider=self.name).observe(time.monotonic() - start)

    def _record_item(self, item_type: str) -> None:
        ITEMS_SCRAPED.labels(spider=self.name, item_type=item_type).inc()

    def _on_error(self, failure):
        url = failure.request.url
        SCRAPE_FAILURE.labels(spider=self.name).inc()
        logger.error("crawl.error", spider=self.name, url=url, error=str(failure.value))
