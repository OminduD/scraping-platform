"""Crawl-job scheduler.

Reads a simple job manifest (JSON array) and enqueues each job into Redis.
In production this would be triggered by a cron / Airflow / Celery beat.

Usage:
    python -m infrastructure.scheduler.scheduler
"""

from __future__ import annotations

import json
import time
from typing import Any

import redis
import structlog

from configs import get_settings

logger = structlog.get_logger(__name__)

QUEUE_KEY = "scraping:jobs"


def get_redis_client() -> redis.Redis:
    settings = get_settings().redis
    return redis.Redis(host=settings.host, port=settings.port, db=settings.db)


def enqueue_job(client: redis.Redis, job: dict[str, Any]) -> None:
    """Push a single crawl job (JSON dict) onto the Redis queue."""
    payload = json.dumps(job)
    client.rpush(QUEUE_KEY, payload)
    logger.info("scheduler.enqueued", spider=job.get("spider"), url=job.get("url"))


def enqueue_manifest(manifest_path: str) -> int:
    """Read a JSON manifest file and enqueue all jobs."""
    with open(manifest_path) as fh:
        jobs: list[dict[str, Any]] = json.load(fh)

    client = get_redis_client()
    for job in jobs:
        job.setdefault("enqueued_at", time.time())
        enqueue_job(client, job)

    logger.info("scheduler.manifest_loaded", total=len(jobs))
    return len(jobs)


def queue_length() -> int:
    """Return the current number of pending jobs."""
    client = get_redis_client()
    return client.llen(QUEUE_KEY)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m infrastructure.scheduler.scheduler <manifest.json>")
        sys.exit(1)
    enqueue_manifest(sys.argv[1])
