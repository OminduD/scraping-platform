# Playwright Spider Development Guide

This guide explains how to create spiders that use Playwright for JavaScript rendering and API interception.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Playwright Spider](#basic-playwright-spider)
3. [API Interception](#api-interception)
4. [CloudFlare Bypass](#cloudflare-bypass)
5. [Site-Specific Examples](#site-specific-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Enable Playwright in Your Spider

```python
from crawlers.base import BaseSpider

class MySpider(BaseSpider):
    name = "myspider"
    use_playwright = True  # Enable Playwright

    def start_requests(self):
        yield self.make_playwright_request(
            "https://example.com",
            self.parse,
            wait_for_selector="div.content"
        )

    def parse(self, response):
        # Parse JavaScript-rendered content
        for item in response.css("div.product"):
            yield {
                "title": item.css("h2::text").get(),
                "price": item.css("span.price::text").get(),
            }
```

### 2. Run Your Spider

```bash
python -m scripts.run_spider myspider --url "https://example.com"
```

---

## Basic Playwright Spider

### Example 1: Simple JS-Rendered Content

For sites that load content dynamically with JavaScript:

```python
from crawlers.base import BaseSpider

class SimplePlaywrightSpider(BaseSpider):
    """Spider for JavaScript-heavy sites."""

    name = "simple_pw"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com/products"]
    use_playwright = True

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="div.product-grid",  # Wait for products to load
                wait_for_timeout=2000,  # Additional 2 second wait
            )

    def parse(self, response):
        self._record_success(response.url)

        # Extract products from rendered page
        for product in response.css("div.product-card"):
            yield {
                "title": product.css("h3.title::text").get(),
                "price": product.css("span.price::text").get(),
                "url": response.urljoin(product.css("a::attr(href)").get()),
                "image": product.css("img::attr(src)").get(),
            }
            self._record_item("product")

        # Follow pagination
        next_page = response.css("a.next-page::attr(href)").get()
        if next_page:
            yield self.make_playwright_request(
                response.urljoin(next_page),
                self.parse,
                wait_for_selector="div.product-grid"
            )
```

---

## API Interception

### Why API Interception?

Many modern websites load data via JSON APIs. Intercepting these APIs gives you:
- **Cleaner data** (structured JSON instead of HTML)
- **Faster parsing** (no CSS selectors needed)
- **More reliable** (less brittle than HTML parsing)

### Example 2: API-First Spider

```python
from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser

class ApiSpider(BaseSpider):
    """Spider using API interception for data extraction."""

    name = "api_spider"
    allowed_domains = ["api-heavy-site.com"]
    start_urls = ["https://api-heavy-site.com/products"]
    use_playwright = True

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_selector="div.loading-complete",
                api_interception_patterns=[
                    "**/api/products**",  # Product API
                    "**/graphql**",       # GraphQL endpoint
                    "**/*.json",          # Any JSON response
                ]
            )

    def parse(self, response):
        self._record_success(response.url)

        # Try API-first approach
        api_data = ApiParser.extract_from_intercepted(response, r"/api/products")

        if api_data:
            # Parse from API (preferred)
            yield from self._parse_from_api(api_data)
        else:
            # Fallback to HTML parsing
            yield from self._parse_from_html(response)

    def _parse_from_api(self, api_data):
        """Extract from API responses (fast, clean)."""
        for item in api_data:
            yield {
                "title": item["name"],
                "price": item["price"],
                "stock": item.get("inventory", {}).get("available", 0),
                "source": "api",
            }
            self._record_item("product")

    def _parse_from_html(self, response):
        """Fallback to HTML parsing."""
        for product in response.css("div.product"):
            yield {
                "title": product.css("h2::text").get(),
                "price": product.css("span.price::text").get(),
                "source": "html",
            }
            self._record_item("product")
```

---

## CloudFlare Bypass

### Example 3: CloudFlare-Protected Site

For sites with CloudFlare or similar protection:

```python
from crawlers.base import BaseSpider

class CloudFlareSpider(BaseSpider):
    """Spider for CloudFlare-protected sites."""

    name = "cloudflare_spider"
    allowed_domains = ["protected-site.com"]
    start_urls = ["https://protected-site.com"]
    use_playwright = True

    playwright_config = {
        "stealth_mode": True,   # REQUIRED for CloudFlare
        "wait_for_timeout": 8000,  # Wait for challenge (5-10 seconds)
    }

    async def start_requests(self):
        for url in self.start_urls:
            yield self.make_playwright_request(
                url,
                self.parse,
                wait_for_timeout=8000,  # CloudFlare challenge time
                screenshot="cloudflare_debug.png",  # Debug screenshot
            )

    async def parse(self, response):
        """Parse after CloudFlare bypass."""
        page = response.meta.get("playwright_page")

        # Verify we bypassed CloudFlare
        if page and await self._has_cloudflare(page):
            self.logger.warning(f"CloudFlare challenge failed: {response.url}")
            return

        self._record_success(response.url)

        # Now parse the page
        for item in response.css("div.product"):
            yield {
                "title": item.css("h2::text").get(),
                "price": item.css("span.price::text").get(),
            }

    async def _has_cloudflare(self, page):
        """Check if CloudFlare challenge is present."""
        try:
            # Check for common CloudFlare indicators
            cf_ray = await page.query_selector("div#cf-wrapper")
            challenge_form = await page.query_selector("form#challenge-form")
            return bool(cf_ray or challenge_form)
        except:
            return False
```

---

## Site-Specific Examples

### Example 4: Yelp Spider

```python
from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser

class YelpSpider(BaseSpider):
    """Scrape Yelp business listings using GraphQL API interception."""

    name = "yelp"
    allowed_domains = ["yelp.com"]
    use_playwright = True

    def start_requests(self):
        # Search URL
        url = "https://www.yelp.com/search?find_desc=restaurants&find_loc=San+Francisco"

        yield self.make_playwright_request(
            url,
            self.parse,
            wait_for_selector="div[data-testid='serp-ia-card']",
            wait_for_timeout=3000,
            api_interception_patterns=[
                "**/gql**",      # GraphQL API
                "**/api/v3/**",  # REST API
            ]
        )

    def parse(self, response):
        self._record_success(response.url)

        # Extract from GraphQL API
        graphql_data = ApiParser.parse_graphql_response(response)

        if graphql_data:
            for business in self._extract_businesses_from_gql(graphql_data):
                yield business
        else:
            # Fallback to HTML
            for card in response.css("div[data-testid='serp-ia-card']"):
                yield {
                    "name": card.css("h3 a::text").get(),
                    "rating": card.css("div[aria-label*='star']::attr(aria-label)").get(),
                    "reviews": card.css("span.reviewCount::text").get(),
                    "category": card.css("span.category::text").get(),
                    "url": response.urljoin(card.css("a::attr(href)").get()),
                    "source": "yelp-html",
                }

    def _extract_businesses_from_gql(self, graphql_data):
        """Extract business data from GraphQL responses."""
        for item in graphql_data:
            if isinstance(item, dict) and "bizId" in item:
                yield {
                    "name": item.get("name"),
                    "rating": item.get("rating"),
                    "reviews": item.get("reviewCount"),
                    "category": item.get("categories", [{}])[0].get("title"),
                    "url": f"https://www.yelp.com/biz/{item['alias']}",
                    "source": "yelp-api",
                }
```

### Example 5: CoinMarketCap Spider

```python
from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser

class CoinMarketCapSpider(BaseSpider):
    """Scrape cryptocurrency data using API interception."""

    name = "coinmarketcap"
    allowed_domains = ["coinmarketcap.com"]
    start_urls = ["https://coinmarketcap.com/"]
    use_playwright = True

    def start_requests(self):
        yield self.make_playwright_request(
            self.start_urls[0],
            self.parse,
            wait_for_selector="table.cmc-table",
            api_interception_patterns=[
                "**/v1/cryptocurrency/listings/**",
                "**/data-api/v3/**",
            ]
        )

    def parse(self, response):
        self._record_success(response.url)

        # Extract from API
        api_data = ApiParser.extract_from_intercepted(
            response,
            r"/cryptocurrency/listings",
            key_path="data"  # Extract data.data from response
        )

        if api_data:
            for crypto in api_data:
                quote = crypto.get("quote", {}).get("USD", {})
                yield {
                    "name": crypto.get("name"),
                    "symbol": crypto.get("symbol"),
                    "price": quote.get("price"),
                    "market_cap": quote.get("market_cap"),
                    "volume_24h": quote.get("volume_24h"),
                    "percent_change_24h": quote.get("percent_change_24h"),
                    "rank": crypto.get("cmc_rank"),
                }
                self._record_item("crypto")
```

---

## Best Practices

### 1. Always Use `wait_for_selector`

Wait for specific content instead of fixed timeouts:

```python
# ✅ Good - waits for content
yield self.make_playwright_request(
    url,
    self.parse,
    wait_for_selector="div.products-loaded"
)

# ❌ Bad - fixed delay (unreliable)
yield self.make_playwright_request(
    url,
    self.parse,
    wait_for_timeout=5000
)
```

### 2. Prefer API Interception Over HTML

API data is cleaner and more reliable:

```python
def parse(self, response):
    # Try API first
    api_data = ApiParser.extract_from_intercepted(response, r"/api/products")
    if api_data:
        yield from self._parse_from_api(api_data)
    else:
        yield from self._parse_from_html(response)
```

### 3. Use Metrics and Logs

Track your spider's performance:

```python
def parse(self, response):
    self._record_success(response.url)  # Track timing

    for item in items:
        yield item
        self._record_item("product")  # Track counts
```

### 4. Handle Errors Gracefully

```python
async def parse(self, response):
    try:
        page = response.meta.get("playwright_page")
        if page:
            await page.wait_for_selector("div.content", timeout=10000)
    except Exception as e:
        self.logger.error(f"Timeout waiting for content: {e}")
        return

    # Continue parsing...
```

### 5. Close Pages to Free Memory

```python
async def parse(self, response):
    page = response.meta.get("playwright_page")
    try:
        # Do your parsing
        pass
    finally:
        if page:
            await page.close()
```

---

## Troubleshooting

### Problem: Bot Detected

**Symptoms**: Access denied, CAPTCHA challenges, 403 errors

**Solutions**:
1. Ensure stealth mode is enabled
2. Check user agent rotation is working
3. Add random delays
4. Use residential proxies (if available)

```python
# Enable all anti-bot features
class MySpider(BaseSpider):
    use_playwright = True
    playwright_config = {
        "stealth_mode": True,
    }
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,  # Random delays
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
```

### Problem: API Not Intercepted

**Symptoms**: `api_responses` is empty

**Solutions**:
1. Check patterns match the actual API URLs (use browser DevTools)
2. Increase `wait_for_timeout` (APIs may load after page)
3. Verify API returns JSON content-type

```python
# Debug: Print all intercepted APIs
api_responses = ApiParser.get_all_api_responses(response)
for api_resp in api_responses:
    self.logger.info(f"Captured: {api_resp['url']}")
```

### Problem: Page Timeout

**Symptoms**: `TimeoutError: waiting for selector`

**Solutions**:
1. Increase timeout
2. Check selector is correct
3. Wait for different element
4. Use `wait_for_timeout` instead

```python
# Increase timeout
yield self.make_playwright_request(
    url,
    self.parse,
    wait_for_selector="div.content",  # Check this selector
)

# Or use fixed delay
yield self.make_playwright_request(
    url,
    self.parse,
    wait_for_timeout=5000
)
```

### Problem: Memory Issues

**Symptoms**: High memory usage, slow performance

**Solutions**:
1. Reduce concurrent Playwright requests
2. Close pages after parsing
3. Use Playwright only when needed

```python
# In settings.py
CONCURRENT_REQUESTS = 4  # Lower for Playwright
PLAYWRIGHT_MAX_CONTEXTS = 2
```

### Problem: CloudFlare Challenge Fails

**Symptoms**: Stuck on CloudFlare page

**Solutions**:
1. Increase `wait_for_timeout` to 10+ seconds
2. Enable stealth mode
3. Check screenshot for actual error
4. May require residential proxies

```python
yield self.make_playwright_request(
    url,
    self.parse,
    wait_for_timeout=10000,  # Wait longer
    screenshot="debug.png",  # Check what's happening
)
```

---

## Testing Your Spider

### 1. Start with Small Test

```bash
# Test with single URL
python -m scripts.run_spider myspider --url "https://example.com/test" --output-json data/raw/test.json

# Check output
cat data/raw/test.json | jq '.'
```

### 2. Check Logs

```bash
# Run with debug logging
python -m scripts.run_spider myspider --url "https://example.com" -s LOG_LEVEL=DEBUG
```

### 3. Save Screenshots

```python
# Add screenshot to debug
yield self.make_playwright_request(
    url,
    self.parse,
    screenshot="debug.png"
)
```

### 4. Test API Interception

```python
def parse(self, response):
    # Debug: Print all APIs
    for api in ApiParser.get_all_api_responses(response):
        self.logger.info(f"API: {api['url']}")
        self.logger.info(f"Body preview: {api['body'][:200]}")
```

---

## Additional Resources

- [Scrapy-Playwright Documentation](https://github.com/scrapy-plugins/scrapy-playwright)
- [Playwright API Reference](https://playwright.dev/python/docs/api/class-playwright)
- [Project Configuration](../configs/playwright.yaml)
- [API Parser Utilities](../crawlers/parsers/api_parser.py)

---

## Need Help?

1. Check the [troubleshooting section](#troubleshooting)
2. Review existing spiders in `crawlers/ecommerce/` and `crawlers/jobs/`
3. Check logs with `LOG_LEVEL=DEBUG`
4. Save screenshots to debug rendering issues
5. Test API patterns in browser DevTools Network tab
