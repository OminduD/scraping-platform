"""Scrapy pipeline that exports items to a styled HTML table on spider close."""

from __future__ import annotations

from pathlib import Path
from html import escape

import structlog

logger = structlog.get_logger(__name__)

OUTPUT_DIR = Path("data/processed")

SPIDER_OUTPUT_FILES = {
    "products": "products.html",
    "jobs": "jobs.html",
}


class HtmlExportPipeline:
    """Collect items during crawl and write an HTML report when the spider closes."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def process_item(self, item):
        self.items.append(dict(item))
        return item

    def close_spider(self) -> None:
        spider_name = self.crawler.spider.name
        filename = SPIDER_OUTPUT_FILES.get(spider_name)
        if not filename:
            logger.warning("html_export.unknown_spider", spider=spider_name)
            return

        if not self.items:
            logger.info("html_export.no_items", spider=spider_name)
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / filename

        headers = list(self.items[0].keys())
        rows_html = []
        for item in self.items:
            cells = "".join(
                f"<td>{escape(str(item.get(h, '')))}</td>" for h in headers
            )
            rows_html.append(f"<tr>{cells}</tr>")

        header_html = "".join(f"<th>{escape(h)}</th>" for h in headers)
        title = f"{spider_name.replace('_', ' ').title()} — Scraped Results"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; background: #f8f9fa; }}
  h1 {{ color: #212529; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  th, td {{ padding: .6rem .8rem; text-align: left; border-bottom: 1px solid #dee2e6; }}
  th {{ background: #343a40; color: #fff; position: sticky; top: 0; }}
  tr:hover {{ background: #f1f3f5; }}
  .meta {{ color: #6c757d; margin-bottom: 1rem; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">{len(self.items)} items</p>
<table>
<thead><tr>{header_html}</tr></thead>
<tbody>
{"".join(rows_html)}
</tbody>
</table>
</body>
</html>"""

        path.write_text(html, encoding="utf-8")
        logger.info("html_export.done", spider=spider_name, path=str(path), count=len(self.items))
