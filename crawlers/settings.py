# Scrapy settings for the scraping-platform project.
BOT_NAME = "scraping_platform"

SPIDER_MODULES = ["crawlers.ecommerce", "crawlers.jobs"]
NEWSPIDER_MODULE = "crawlers"

ROBOTSTXT_OBEY = True

DOWNLOAD_DELAY = 1.5
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
}

ITEM_PIPELINES = {
    "pipelines.extract.html_parser.HtmlCleanPipeline": 100,
    "pipelines.transform.cleaner.TransformPipeline": 200,
    "pipelines.load.db_loader.DatabasePipeline": 300,
}

LOG_LEVEL = "INFO"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
