"""Run a spider by name.

Usage:
    python -m scripts.run_spider products
    python -m scripts.run_spider jobs
    python -m scripts.run_spider products --url https://example.com
    python -m scripts.run_spider products --urls https://a.com https://b.com
    python -m scripts.run_spider products --url-file configs/urls.txt
    python -m scripts.run_spider products --url https://example.com --sitemap
    python -m scripts.run_spider products --sitemap-url https://example.com/sitemap.xml
    python -m scripts.run_spider products --download-images

Priority: --url/--urls > --url-file > spider default start_urls
Sitemap: --sitemap auto-discovers sitemap.xml from base URL, --sitemap-url for explicit sitemap.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

SPIDERS = {
    "products": "crawlers.ecommerce.product_spider.ProductSpider",
    "jobs": "crawlers.jobs.job_spider.JobSpider",
}


def load_urls_from_file(filepath: str) -> list[str]:
    """Read URLs from a text file, one per line. Skips comments (#) and blanks."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"URL file not found: {filepath}")
    urls = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    if not urls:
        raise ValueError(f"No URLs found in file: {filepath}")
    return urls


def derive_sitemap_urls(base_urls: list[str]) -> list[str]:
    """Derive sitemap URLs from base URLs by appending /sitemap.xml."""
    sitemap_urls = []
    for url in base_urls:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        sitemap_urls.append(urljoin(base, "/sitemap.xml"))
    return list(set(sitemap_urls))  # deduplicate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a spider by name")
    parser.add_argument("spider", choices=SPIDERS.keys(), help="Spider to run")

    url_group = parser.add_mutually_exclusive_group()
    url_group.add_argument("--url", help="Override with a single start URL")
    url_group.add_argument("--urls", nargs="+", help="Override with multiple start URLs")
    url_group.add_argument("--url-file", help="Path to a text file with URLs (one per line)")

    parser.add_argument(
        "--sitemap",
        action="store_true",
        help="Enable sitemap discovery mode. Tries to find sitemap.xml from the base URL. "
             "Use with --url or --urls. Example: --url https://example.com --sitemap",
    )
    parser.add_argument(
        "--sitemap-url",
        nargs="+",
        metavar="URL",
        help="Explicit sitemap URL(s) to use. Example: --sitemap-url https://example.com/sitemap.xml",
    )
    parser.add_argument(
        "--output-json",
        help="Write raw scraped items to this JSON file (overrides spider FEEDS).",
    )
    parser.add_argument(
        "--download-images",
        action="store_true",
        help="Download product images to IMAGES_STORE. By default only image URLs are saved.",
    )

    args = parser.parse_args()

    dotted_path = SPIDERS[args.spider]
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    spider_cls = getattr(module, class_name)

    settings = get_project_settings()
    settings.setmodule("crawlers.settings")

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        settings.set(
            "FEEDS",
            {
                str(output_path): {
                    "format": "json",
                    "encoding": "utf-8",
                    "overwrite": True,
                }
            },
            priority="cmdline",
        )

    process = CrawlerProcess(settings)

    kwargs = {}
    if args.url:
        kwargs["start_urls"] = [args.url]
    elif args.urls:
        kwargs["start_urls"] = args.urls
    elif args.url_file:
        kwargs["start_urls"] = load_urls_from_file(args.url_file)

    # Handle sitemap modes
    if args.sitemap_url:
        # Explicit sitemap URL(s) provided
        kwargs["sitemap_urls"] = args.sitemap_url
    elif args.sitemap:
        # Auto-discover sitemap from base URL(s)
        base_urls = kwargs.get("start_urls", [])
        if not base_urls:
            parser.error("--sitemap requires --url, --urls, or --url-file to derive sitemap URLs")
        kwargs["sitemap_urls"] = derive_sitemap_urls(base_urls)
        # Clear start_urls since sitemap will provide them
        kwargs.pop("start_urls", None)

    kwargs["download_images"] = args.download_images

    process.crawl(spider_cls, **kwargs)
    process.start()


if __name__ == "__main__":
    main()
