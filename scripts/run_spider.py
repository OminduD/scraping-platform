"""Run a spider by name.

Usage:
    python -m scripts.run_spider products
    python -m scripts.run_spider jobs
"""

from __future__ import annotations

import sys

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

SPIDERS = {
    "products": "crawlers.ecommerce.product_spider.ProductSpider",
    "jobs": "crawlers.jobs.job_spider.JobSpider",
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in SPIDERS:
        print(f"Usage: python -m scripts.run_spider <{'|'.join(SPIDERS)}>")
        sys.exit(1)

    spider_name = sys.argv[1]
    dotted_path = SPIDERS[spider_name]
    module_path, class_name = dotted_path.rsplit(".", 1)

    import importlib
    module = importlib.import_module(module_path)
    spider_cls = getattr(module, class_name)

    settings = get_project_settings()
    settings.setmodule("crawlers.settings")
    process = CrawlerProcess(settings)
    process.crawl(spider_cls)
    process.start()


if __name__ == "__main__":
    main()
