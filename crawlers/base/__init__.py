"""Base spider with shared configuration, logging, metrics, and sitemap support."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import scrapy
import structlog
from prometheus_client import Counter, Histogram

from configs import get_settings
from crawlers.base.sitemap import filter_urls, parse_sitemap_xml

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
    - Sitemap-based URL discovery (set ``sitemap_urls`` or pass ``--sitemap``).
    """

    name = "base"

    custom_settings: dict[str, Any] = {}

    # ── Sitemap support ──────────────────────────────────────────────
    # Set these on a subclass or pass sitemap_urls via kwargs.
    sitemap_urls: list[str] = []
    sitemap_filter_patterns: list[str] = []  # regex patterns to keep only matching URLs

    def __init__(self, *args: Any, sitemap_urls: list[str] | None = None, **kwargs: Any) -> None:
        if sitemap_urls:
            self.sitemap_urls = sitemap_urls
        super().__init__(*args, **kwargs)
        settings = get_settings().crawler
        self.custom_settings.setdefault("DOWNLOAD_DELAY", settings.crawl_delay)
        self.custom_settings.setdefault("RETRY_TIMES", settings.max_retries)
        self.custom_settings.setdefault("CONCURRENT_REQUESTS", settings.concurrent_requests)
        self._request_start_times: dict[str, float] = {}

    # ── Hooks ────────────────────────────────────────────────────────

    def start_requests(self):
        if self.sitemap_urls:
            for url in self.sitemap_urls:
                logger.info("sitemap.fetch", spider=self.name, url=url)
                yield scrapy.Request(url, callback=self._parse_sitemap, errback=self._on_error)
        else:
            for url in self.start_urls:
                logger.info("crawl.start", spider=self.name, url=url)
                yield scrapy.Request(url, callback=self.parse, errback=self._on_error)

    def _parse_sitemap(self, response):
        """Parse a sitemap XML response and follow discovered URLs."""
        page_urls, nested_sitemaps = parse_sitemap_xml(response.body)

        # Follow nested sitemap index entries
        for sitemap_url in nested_sitemaps:
            logger.info("sitemap.nested", spider=self.name, url=sitemap_url)
            yield scrapy.Request(sitemap_url, callback=self._parse_sitemap, errback=self._on_error)

        # Filter and follow page URLs
        urls = filter_urls(page_urls, self.sitemap_filter_patterns)
        logger.info("sitemap.discovered", spider=self.name, total=len(page_urls), filtered=len(urls), source=response.url)

        # Derive allowed_domains from sitemap URLs if not already set
        if urls and not getattr(self, "_domains_set_from_sitemap", False):
            new_domains = {urlparse(u).hostname for u in urls if urlparse(u).hostname}
            existing = set(getattr(self, "allowed_domains", []) or [])
            self.allowed_domains = list(existing | new_domains)
            self._domains_set_from_sitemap = True

        for url in urls:
            self._record_start(url)
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
