"""Run a spider by name.

Usage:
    python -m scripts.run_spider products
    python -m scripts.run_spider jobs
    python -m scripts.run_spider products --url https://example.com
    python -m scripts.run_spider products --urls https://a.com https://b.com
    python -m scripts.run_spider products --url-file configs/urls.txt

Priority: --url/--urls > --url-file > spider default start_urls
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a spider by name")
    parser.add_argument("spider", choices=SPIDERS.keys(), help="Spider to run")

    url_group = parser.add_mutually_exclusive_group()
    url_group.add_argument("--url", help="Override with a single start URL")
    url_group.add_argument("--urls", nargs="+", help="Override with multiple start URLs")
    url_group.add_argument("--url-file", help="Path to a text file with URLs (one per line)")

    args = parser.parse_args()

    dotted_path = SPIDERS[args.spider]
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    spider_cls = getattr(module, class_name)

    settings = get_project_settings()
    settings.setmodule("crawlers.settings")
    process = CrawlerProcess(settings)

    kwargs = {}
    if args.url:
        kwargs["start_urls"] = [args.url]
    elif args.urls:
        kwargs["start_urls"] = args.urls
    elif args.url_file:
        kwargs["start_urls"] = load_urls_from_file(args.url_file)

    process.crawl(spider_cls, **kwargs)
    process.start()


if __name__ == "__main__":
    main()
