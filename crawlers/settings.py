# Scrapy settings for the scraping-platform project.
BOT_NAME = "scraping_platform"

SPIDER_MODULES = ["crawlers.ecommerce", "crawlers.jobs", "crawlers.business", "crawlers.crypto"]
NEWSPIDER_MODULE = "crawlers"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

ROBOTSTXT_OBEY = False

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
    "scrapy.pipelines.images.ImagesPipeline": 50,
    "pipelines.extract.html_parser.HtmlCleanPipeline": 100,
    "pipelines.transform.cleaner.TransformPipeline": 200,
    "pipelines.load.db_loader.DatabasePipeline": 300,
    "pipelines.export.json_exporter.JsonExportPipeline": 400,
}

# ── Image downloading ────────────────────────────────────────────────
IMAGES_STORE = "data/images"
IMAGES_URLS_FIELD = "image_urls"
IMAGES_RESULT_FIELD = "images"

LOG_LEVEL = "INFO"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# ── Playwright Configuration ────────────────────────────────────────
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 30000,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-web-security",
    ],
}

PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "ignore_https_errors": True,
    },
}

PLAYWRIGHT_MAX_CONTEXTS = 4
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 2
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000

# ── Middleware Configuration ────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "crawlers.middleware.user_agent.RandomUserAgentMiddleware": 400,
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

SPIDER_MIDDLEWARES = {
    "crawlers.middleware.stealth.PlaywrightStealthMiddleware": 585,
    "crawlers.middleware.api_interceptor.ApiInterceptorMiddleware": 590,
}
