"""Distributed worker — pulls crawl jobs from Redis and executes spiders.

Each worker is a long-running process designed to be horizontally scaled
via Docker Compose replicas or Kubernetes pods.

Crawl jobs are executed in subprocesses to avoid the Twisted reactor
"not restartable" limitation.

Usage:
    python -m infrastructure.workers.worker
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
from typing import Any

import redis
import structlog

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


def process_job(job: dict[str, Any]) -> bool:
    """Run a single crawl job in a subprocess to avoid reactor restart issues."""
    spider_name = job.get("spider")
    if spider_name not in SPIDER_REGISTRY:
        logger.error("worker.unknown_spider", spider=spider_name)
        return False

    # Run the spider via scripts.run_spider in a child process
    cmd = [sys.executable, "-m", "scripts.run_spider", spider_name]
    if "url" in job:
        cmd.extend(["--url", job["url"]])

    logger.info("worker.starting_crawl", spider=spider_name, cmd=cmd)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(
            "worker.crawl_failed",
            spider=spider_name,
            returncode=result.returncode,
            stderr=result.stderr[-500:] if result.stderr else "",
        )
        return False

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
