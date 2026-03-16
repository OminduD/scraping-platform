"""Distributed worker — pulls crawl jobs from Redis and executes spiders.

Each worker is a long-running process designed to be horizontally scaled
via Docker Compose replicas or Kubernetes pods.

Usage:
    python -m infrastructure.workers.worker
"""

from __future__ import annotations

import json
import signal
import sys
import time
from typing import Any

import redis
import structlog
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from configs import get_settings
from infrastructure.scheduler.scheduler import QUEUE_KEY

logger = structlog.get_logger(__name__)

# Spider registry — maps spider name → importable class path
SPIDER_REGISTRY: dict[str, str] = {
    "products": "crawlers.ecommerce.product_spider.ProductSpider",
    "jobs": "crawlers.jobs.job_spider.JobSpider",
}

_shutdown_requested = False


def _handle_signal(signum: int, frame) -> None:  # noqa: ANN001
    global _shutdown_requested
    logger.info("worker.shutdown_requested", signal=signum)
    _shutdown_requested = True


def _import_spider(dotted_path: str):
    """Dynamically import a spider class from its dotted path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def process_job(job: dict[str, Any]) -> bool:
    """Run a single crawl job synchronously using CrawlerProcess."""
    spider_name = job.get("spider")
    if spider_name not in SPIDER_REGISTRY:
        logger.error("worker.unknown_spider", spider=spider_name)
        return False

    spider_cls = _import_spider(SPIDER_REGISTRY[spider_name])

    # Build Scrapy settings; override start_urls if the job provides one
    settings = get_project_settings()
    settings.setmodule("crawlers.settings")
    process = CrawlerProcess(settings)

    kwargs: dict[str, Any] = {}
    if "url" in job:
        kwargs["start_urls"] = [job["url"]]

    process.crawl(spider_cls, **kwargs)
    process.start(stop_after_crawl=True)
    logger.info("worker.job_done", spider=spider_name)
    return True


def run_worker_loop() -> None:
    """Main worker loop — block-pops jobs from Redis and processes them."""
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    cfg = get_settings().redis
    client = redis.Redis(host=cfg.host, port=cfg.port, db=cfg.db)

    logger.info("worker.started")

    while not _shutdown_requested:
        # BLPOP with a 5-second timeout so we can check shutdown flag
        result = client.blpop(QUEUE_KEY, timeout=5)
        if result is None:
            continue

        _, raw = result
        try:
            job = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("worker.invalid_payload", raw=raw)
            continue

        logger.info("worker.job_received", job=job)
        try:
            process_job(job)
        except Exception:
            logger.exception("worker.job_failed", job=job)

    logger.info("worker.stopped")


if __name__ == "__main__":
    run_worker_loop()
