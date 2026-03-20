"""User agent rotation middleware for avoiding fingerprinting.

This middleware randomly rotates user agents for each request to make
scraping traffic appear more diverse and avoid detection.
"""

from __future__ import annotations

import random

import structlog
from fake_useragent import UserAgent
from scrapy import Spider, signals
from scrapy.http import Request

logger = structlog.get_logger(__name__)


class RandomUserAgentMiddleware:
    """Rotate user agents for each request to avoid fingerprinting.

    This middleware:
    - Uses fake-useragent library for realistic user agents
    - Rotates on every request
    - Supports browser type filtering (chrome, firefox, safari)
    - Can be disabled per-request via meta['skip_user_agent_rotation']
    """

    def __init__(self):
        """Initialize user agent generator."""
        try:
            self.ua = UserAgent()
            logger.info("user_agent.middleware.enabled", status="initialized")
        except Exception as e:
            logger.warning("user_agent.middleware.init_failed", error=str(e))
            self.ua = None

    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware instance from crawler."""
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider: Spider):
        """Log when spider starts."""
        logger.info("user_agent.middleware.spider_started", spider=spider.name)

    def process_request(self, request: Request, spider: Spider):
        """Set a random user agent for each request.

        Args:
            request: Scrapy request object
            spider: Spider instance

        Returns:
            None (modifies request in place)
        """
        # Skip if explicitly disabled
        if request.meta.get("skip_user_agent_rotation"):
            return None

        # Skip if UA library failed to initialize
        if not self.ua:
            return None

        # Get random user agent
        try:
            # Prefer Chrome user agents (most common, best compatibility)
            user_agent = self.ua.chrome
        except Exception:
            # Fallback to random if chrome fails
            try:
                user_agent = self.ua.random
            except Exception as e:
                logger.warning("user_agent.generation_failed", error=str(e))
                return None

        # Set user agent header
        request.headers["User-Agent"] = user_agent

        # Also update Playwright context if this is a Playwright request
        if request.meta.get("playwright"):
            playwright_context = request.meta.get("playwright_context", "default")
            request.meta.setdefault("playwright_context_kwargs", {})
            request.meta["playwright_context_kwargs"]["user_agent"] = user_agent

        logger.debug(
            "user_agent.rotated",
            spider=spider.name,
            url=request.url,
            user_agent=user_agent[:50] + "..."  # Log first 50 chars
        )

        return None
