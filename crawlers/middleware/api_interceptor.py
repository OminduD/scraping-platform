"""API interception middleware for capturing XHR/Fetch requests.

This middleware captures API calls made by JavaScript applications and stores
their responses, allowing spiders to extract data directly from JSON APIs
instead of parsing HTML.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from scrapy import Spider, signals
from scrapy.http import Request, Response
from twisted.internet.defer import inlineCallbacks

logger = structlog.get_logger(__name__)


class ApiInterceptorMiddleware:
    """Intercept and capture API requests/responses from Playwright pages.

    This middleware:
    - Listens to all network requests on the page
    - Captures responses from API endpoints matching patterns
    - Stores captured data in response.meta['api_responses']
    - Allows spiders to parse JSON directly instead of HTML

    Usage in spider:
        yield self.make_playwright_request(
            url,
            self.parse,
            api_interception_patterns=["**/api/**", "**/graphql**"]
        )

        def parse(self, response):
            api_responses = response.meta.get('api_responses', [])
            for api_resp in api_responses:
                data = json.loads(api_resp['body'])
                # Parse JSON data
    """

    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware instance from crawler."""
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider: Spider):
        """Log when spider starts."""
        logger.info("api_interceptor.middleware.enabled", spider=spider.name)

    @inlineCallbacks
    def process_request(self, request: Request, spider: Spider):
        """Set up API interception for Playwright requests.

        Args:
            request: Scrapy request object
            spider: Spider instance

        Returns:
            None (middleware continues processing)
        """
        # Only process Playwright requests
        if not request.meta.get("playwright"):
            return None

        # Check if API interception is requested
        patterns = request.meta.get("api_interception_patterns")
        if not patterns:
            return None

        # Store patterns in meta for the response handler
        request.meta["_api_patterns"] = patterns
        request.meta.setdefault("playwright_page_coroutines", [])

        # Add page coroutine to set up route interception
        async def setup_interception(page, request):
            """Set up route interception on the page."""
            captured = []

            async def intercept_route(route):
                """Intercept matching API routes."""
                req = route.request
                url = req.url
                method = req.method

                # Check if URL matches any pattern
                matches = any(self._matches_pattern(url, pattern) for pattern in patterns)

                if matches:
                    logger.debug("api_interceptor.route_matched", url=url, method=method)

                    try:
                        # Fetch the response
                        response = await route.fetch()

                        # Check if it's JSON
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type or "application/json" in content_type:
                            body = await response.text()

                            captured.append({
                                "url": url,
                                "method": method,
                                "status": response.status,
                                "headers": dict(response.headers),
                                "body": body,
                            })

                            logger.info(
                                "api_interceptor.captured",
                                url=url,
                                status=response.status,
                                size=len(body)
                            )

                        # Fulfill the route with the response
                        await route.fulfill(response=response)

                    except Exception as e:
                        logger.error("api_interceptor.error", url=url, error=str(e))
                        await route.continue_()
                else:
                    # Let non-matching requests through
                    await route.continue_()

            # Set up route interception for all patterns
            await page.route("**/*", intercept_route)

            # Store captured responses in page object for later retrieval
            page._captured_apis = captured

            logger.info("api_interceptor.setup_complete", patterns=patterns)

        request.meta["playwright_page_coroutines"].append(setup_interception)

        return None

    def process_response(self, request: Request, response: Response, spider: Spider):
        """Extract captured API responses and attach to response.meta.

        Args:
            request: Scrapy request object
            response: Scrapy response object
            spider: Spider instance

        Returns:
            Response with api_responses in meta
        """
        # Check if this was an API interception request
        if not request.meta.get("_api_patterns"):
            return response

        # Extract captured APIs from page
        page = response.meta.get("playwright_page")
        if page and hasattr(page, "_captured_apis"):
            captured = page._captured_apis
            response.meta["api_responses"] = captured

            logger.info(
                "api_interceptor.responses_attached",
                spider=spider.name,
                url=request.url,
                count=len(captured)
            )
        else:
            response.meta["api_responses"] = []
            logger.debug(
                "api_interceptor.no_captures",
                spider=spider.name,
                url=request.url
            )

        return response

    def _matches_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches glob pattern.

        Args:
            url: URL to check
            pattern: Glob pattern (e.g., "**/api/**", "**graphql**")

        Returns:
            True if URL matches pattern
        """
        import fnmatch

        # Convert glob pattern to work with full URLs
        # Simple implementation - can be enhanced with regex
        if pattern.startswith("**/"):
            pattern = "*" + pattern[2:]

        return fnmatch.fnmatch(url, pattern) or pattern in url
