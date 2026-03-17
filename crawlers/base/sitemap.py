"""Sitemap parsing utilities for URL discovery.

Handles standard sitemaps and sitemap index files (nested sitemaps).
Works with any spider via BaseSpider's built-in sitemap support.
"""

from __future__ import annotations

import re
from typing import Iterator

from lxml import etree
import structlog

logger = structlog.get_logger(__name__)

# XML namespaces used in sitemaps
SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def parse_sitemap_xml(body: bytes) -> tuple[list[str], list[str]]:
    """Parse sitemap XML and return (page_urls, nested_sitemap_urls).

    Handles both:
    - <sitemapindex> → returns nested sitemap URLs
    - <urlset> → returns page URLs
    """
    page_urls: list[str] = []
    sitemap_urls: list[str] = []

    try:
        root = etree.fromstring(body)
    except etree.XMLSyntaxError:
        logger.warning("sitemap.parse_error", reason="invalid XML")
        return page_urls, sitemap_urls

    tag = etree.QName(root.tag).localname if root.tag else ""

    if tag == "sitemapindex":
        for loc in root.findall(".//sm:sitemap/sm:loc", SITEMAP_NS):
            if loc.text:
                sitemap_urls.append(loc.text.strip())
    elif tag == "urlset":
        for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
            if loc.text:
                page_urls.append(loc.text.strip())
    else:
        # Try without namespace (some sitemaps omit it)
        for loc in root.iter("loc"):
            if loc.text:
                page_urls.append(loc.text.strip())

    return page_urls, sitemap_urls


def filter_urls(urls: list[str], patterns: list[str]) -> list[str]:
    """Filter URLs by regex patterns. If patterns is empty, return all URLs."""
    if not patterns:
        return urls
    compiled = [re.compile(p) for p in patterns]
    return [url for url in urls if any(r.search(url) for r in compiled)]
