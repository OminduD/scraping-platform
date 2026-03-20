"""Utilities for parsing intercepted API responses.

These helpers make it easier to extract data from JSON APIs captured
by the API interceptor middleware.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ApiParser:
    """Helper utilities for parsing intercepted API responses."""

    @staticmethod
    def extract_from_intercepted(
        response,
        url_pattern: str,
        key_path: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract data from intercepted API responses matching a URL pattern.

        Args:
            response: Scrapy response object (must have api_responses in meta)
            url_pattern: Regex pattern to match API URLs (e.g., r"/api/products")
            key_path: Optional JSON path to extract (e.g., "data.items")

        Returns:
            List of parsed JSON objects from matching APIs

        Example:
            # Get all GraphQL responses
            data = ApiParser.extract_from_intercepted(response, r"/graphql")

            # Get product data from specific endpoint
            products = ApiParser.extract_from_intercepted(
                response,
                r"/api/v1/products",
                key_path="data.products"
            )
        """
        api_responses = response.meta.get("api_responses", [])

        if not api_responses:
            logger.debug("api_parser.no_responses", url=response.url)
            return []

        # Find matching API responses
        matching = []
        for api_resp in api_responses:
            if re.search(url_pattern, api_resp["url"]):
                try:
                    data = json.loads(api_resp["body"])

                    # Extract from key path if specified
                    if key_path:
                        data = ApiParser._get_nested_value(data, key_path)

                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        matching.extend(data)
                    elif data:
                        matching.append(data)

                    logger.debug(
                        "api_parser.matched",
                        pattern=url_pattern,
                        url=api_resp["url"],
                        items=len(matching)
                    )

                except json.JSONDecodeError as e:
                    logger.warning(
                        "api_parser.json_error",
                        url=api_resp["url"],
                        error=str(e)
                    )
                except Exception as e:
                    logger.error(
                        "api_parser.error",
                        url=api_resp["url"],
                        error=str(e)
                    )

        return matching

    @staticmethod
    def _get_nested_value(data: Any, key_path: str) -> Any:
        """Extract nested value from JSON using dot notation.

        Args:
            data: JSON data (dict or list)
            key_path: Dot-separated path (e.g., "data.items", "results[0].products")

        Returns:
            Extracted value or None if path not found

        Example:
            data = {"data": {"products": [{"id": 1}, {"id": 2}]}}
            result = _get_nested_value(data, "data.products")
            # Returns: [{"id": 1}, {"id": 2}]
        """
        keys = key_path.split(".")
        value = data

        for key in keys:
            # Handle array indexing (e.g., "items[0]")
            array_match = re.match(r"^(.+)\[(\d+)\]$", key)
            if array_match:
                key, index = array_match.groups()
                value = value.get(key, [])[int(index)]
            elif isinstance(value, dict):
                value = value.get(key)
            else:
                return None

            if value is None:
                return None

        return value

    @staticmethod
    def parse_graphql_response(
        response,
        operation_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract data from GraphQL API responses.

        Args:
            response: Scrapy response object with api_responses
            operation_name: Optional GraphQL operation name to filter

        Returns:
            List of data objects from GraphQL responses

        Example:
            # Get all GraphQL data
            data = ApiParser.parse_graphql_response(response)

            # Get specific operation
            products = ApiParser.parse_graphql_response(response, "GetProducts")
        """
        results = []
        api_responses = response.meta.get("api_responses", [])

        for api_resp in api_responses:
            # Check if this is a GraphQL endpoint
            if not re.search(r"/(graphql|gql)", api_resp["url"]):
                continue

            try:
                data = json.loads(api_resp["body"])

                # GraphQL responses typically have structure:
                # { "data": { "operationName": {...} } }
                if "data" in data:
                    gql_data = data["data"]

                    # Filter by operation name if specified
                    if operation_name:
                        if operation_name in gql_data:
                            results.append(gql_data[operation_name])
                    else:
                        # Return all data from this response
                        for value in gql_data.values():
                            if isinstance(value, list):
                                results.extend(value)
                            elif value:
                                results.append(value)

                logger.debug(
                    "api_parser.graphql_parsed",
                    url=api_resp["url"],
                    operation=operation_name,
                    items=len(results)
                )

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(
                    "api_parser.graphql_error",
                    url=api_resp["url"],
                    error=str(e)
                )

        return results

    @staticmethod
    def get_all_api_responses(response) -> list[dict[str, Any]]:
        """Get all intercepted API responses (no filtering).

        Args:
            response: Scrapy response object

        Returns:
            List of all captured API responses with metadata

        Example:
            for api_resp in ApiParser.get_all_api_responses(response):
                print(f"URL: {api_resp['url']}")
                print(f"Status: {api_resp['status']}")
                print(f"Body: {api_resp['body']}")
        """
        return response.meta.get("api_responses", [])

    @staticmethod
    def find_json_in_html(response) -> list[dict[str, Any]]:
        """Extract JSON data embedded in HTML (fallback when API interception fails).

        Looks for common patterns:
        - <script type="application/ld+json">
        - <script id="__NEXT_DATA__">
        - window.__INITIAL_STATE__
        - window.__APOLLO_STATE__

        Args:
            response: Scrapy response object

        Returns:
            List of parsed JSON objects found in HTML

        Example:
            json_data = ApiParser.find_json_in_html(response)
            for data in json_data:
                # Process embedded JSON
        """
        found = []

        # JSON-LD structured data
        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
                found.append({"source": "json-ld", "data": data})
            except json.JSONDecodeError:
                continue

        # Next.js data
        next_data = response.css('script#__NEXT_DATA__::text').get()
        if next_data:
            try:
                data = json.loads(next_data)
                found.append({"source": "next-data", "data": data})
            except json.JSONDecodeError:
                pass

        # Window variables (common pattern: window.__INITIAL_STATE__ = {...})
        for script in response.css("script:not([src])::text").getall():
            # Look for window.VAR = JSON pattern
            matches = re.findall(
                r"window\.__\w+__\s*=\s*({.+?});",
                script,
                re.DOTALL
            )
            for match in matches:
                try:
                    data = json.loads(match)
                    found.append({"source": "window-var", "data": data})
                except json.JSONDecodeError:
                    continue

        logger.debug(
            "api_parser.html_json_found",
            url=response.url,
            count=len(found)
        )

        return found
