"""Run a spider by name.

Usage:
    python -m scripts.run_spider products
    python -m scripts.run_spider jobs
    python -m scripts.run_spider products --url https://example.com
"""

from __future__ import annotations

import argparse
import importlib

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

SPIDERS = {
    "products": "crawlers.ecommerce.product_spider.ProductSpider",
    "jobs": "crawlers.jobs.job_spider.JobSpider",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a spider by name")
    parser.add_argument("spider", choices=SPIDERS.keys(), help="Spider to run")
    parser.add_argument("--url", help="Override start URL")
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

    process.crawl(spider_cls, **kwargs)
    process.start()


if __name__ == "__main__":
    main()
