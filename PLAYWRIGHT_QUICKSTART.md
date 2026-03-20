# Playwright Framework - Quick Start Guide

## What Was Implemented

Your scraping platform now supports:
- ✅ **JavaScript rendering** via Scrapy-Playwright
- ✅ **API interception** to capture JSON responses
- ✅ **Anti-bot evasion** (stealth mode, user agent rotation)
- ✅ **Flexible configuration** (per-domain settings)

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Playwright browsers
playwright install chromium

# 3. Verify installation
python -c "from scrapy_playwright.handler import ScrapyPlaywrightDownloadHandler; print('✓ Ready!')"
```

## Creating Your First Playwright Spider

### Quick Example: Yelp Spider

```python
# File: crawlers/business/yelp_spider.py

from crawlers.base import BaseSpider
from crawlers.parsers.api_parser import ApiParser

class YelpSpider(BaseSpider):
    name = "yelp"
    allowed_domains = ["yelp.com"]
    use_playwright = True

    def start_requests(self):
        url = "https://www.yelp.com/search?find_desc=restaurants&find_loc=San+Francisco"

        yield self.make_playwright_request(
            url,
            self.parse,
            wait_for_selector="div[data-testid='serp-ia-card']",
            api_interception_patterns=["**/gql**", "**/api/v3/**"]
        )

    def parse(self, response):
        self._record_success(response.url)

        # Try API first
        graphql_data = ApiParser.parse_graphql_response(response)
        if graphql_data:
            for business in graphql_data:
                yield {
                    "name": business.get("name"),
                    "rating": business.get("rating"),
                    "url": f"https://yelp.com/biz/{business.get('alias', '')}",
                }
                self._record_item("business")
        else:
            # Fallback to HTML
            for card in response.css("div[data-testid='serp-ia-card']"):
                yield {
                    "name": card.css("h3 a::text").get(),
                    "rating": card.css("span[aria-label*='star']::text").get(),
                    "url": response.urljoin(card.css("a::attr(href)").get()),
                }
                self._record_item("business")
```

### Register Your Spider

```python
# File: scripts/run_spider.py

SPIDERS = {
    "products": "crawlers.ecommerce.product_spider.ProductSpider",
    "jobs": "crawlers.jobs.job_spider.JobSpider",
    "yelp": "crawlers.business.yelp_spider.YelpSpider",  # Add this
}
```

### Run Your Spider

```bash
python -m scripts.run_spider yelp \
    --url "https://www.yelp.com/search?find_desc=pizza&find_loc=NYC" \
    --output-json data/raw/yelp_results.json
```

## Testing the Framework

### Test 1: Basic Playwright Rendering

Use existing ProductSpider with Playwright:

```bash
python -m scripts.run_spider products \
    --url "https://books.toscrape.com" \
    --playwright \
    --screenshot test.png \
    --output-json data/raw/test.json
```

Check:
- ✅ Screenshot saved to `test.png`
- ✅ Data exported to `data/raw/test.json`
- ✅ Logs show `[stealth] Anti-detection scripts loaded`

### Test 2: Stealth Mode Verification

Test against bot detection:

```bash
python -m scripts.run_spider products \
    --url "https://bot.sannysoft.com/" \
    --playwright \
    --screenshot bot_test.png
```

Open `bot_test.png` - should show:
- ✅ "Webdriver: false" or "Bot detected: No"
- ✅ Chrome object present

### Test 3: API Interception

Create a test spider and check logs for captured APIs:

```bash
python -m scripts.run_spider products \
    --url "https://api-heavy-site.com" \
    --playwright \
    -s LOG_LEVEL=DEBUG
```

Look for log lines:
```
[api_interceptor.captured] url=.../api/products status=200 size=12453
[api_interceptor.responses_attached] count=5
```

## Key Features

### 1. `make_playwright_request()` Helper

```python
# Basic usage
yield self.make_playwright_request(url, self.parse)

# With wait conditions
yield self.make_playwright_request(
    url,
    self.parse,
    wait_for_selector="div.loaded",  # Wait for element
    wait_for_timeout=3000,            # Additional fixed delay
)

# With screenshot
yield self.make_playwright_request(
    url,
    self.parse,
    screenshot="debug.png"
)

# With API interception
yield self.make_playwright_request(
    url,
    self.parse,
    api_interception_patterns=["**/api/**", "**/graphql**"]
)
```

### 2. API Response Parsing

```python
from crawlers.parsers.api_parser import ApiParser

def parse(self, response):
    # Get all API responses
    all_apis = ApiParser.get_all_api_responses(response)

    # Filter by URL pattern
    products = ApiParser.extract_from_intercepted(response, r"/api/products")

    # Parse GraphQL
    gql_data = ApiParser.parse_graphql_response(response)

    # Extract nested data
    items = ApiParser.extract_from_intercepted(response, r"/api/search", key_path="data.items")
```

### 3. Configuration via YAML

Configure per-domain settings in `configs/playwright.yaml`:

```yaml
domains:
  yoursite.com:
    enabled: true
    wait_for_selector: "div.products"
    api_interception_patterns:
      - "**/api/**"
```

## Common Patterns

### Pattern 1: Hybrid (API + HTML Fallback)

```python
def parse(self, response):
    # Try API first
    api_data = ApiParser.extract_from_intercepted(response, r"/api/products")

    if api_data:
        yield from self._parse_api(api_data)
    else:
        yield from self._parse_html(response)
```

### Pattern 2: CloudFlare Sites

```python
async def parse(self, response):
    page = response.meta.get("playwright_page")

    # Wait for CloudFlare challenge
    if page:
        await page.wait_for_timeout(8000)
        # Check if bypassed
        if await page.query_selector("div#cf-wrapper"):
            self.logger.error("CloudFlare challenge failed")
            return

    # Now parse the page
    ...
```

### Pattern 3: Infinite Scroll

```python
async def parse(self, response):
    page = response.meta.get("playwright_page")

    # Scroll to load more items
    for i in range(5):  # Scroll 5 times
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

    # Now parse all loaded items
    for item in response.css("div.product"):
        yield {...}
```

## Next Steps

1. **Read the full guide**: `docs/playwright_spider_guide.md`
2. **Check configuration**: `configs/playwright.yaml`
3. **Review examples**: See patterns above
4. **Create your spiders**: Use the templates for Yelp, CoinMarketCap, AliExpress, eBay

## Configuration Reference

### Spider-Level Settings

```python
class MySpider(BaseSpider):
    use_playwright = True  # Enable Playwright

    playwright_config = {
        "stealth_mode": True,
        "wait_for_selector": "div.content",
        "api_interception_patterns": ["**/api/**"],
    }
```

### CLI Overrides

```bash
# Force Playwright on
python -m scripts.run_spider products --playwright

# Headed mode (see browser)
python -m scripts.run_spider products --playwright --headless false

# Save screenshot
python -m scripts.run_spider products --playwright --screenshot debug.png
```

---

## Performance Tips

1. **Use Playwright selectively** - Only for JS-heavy sites
2. **Prefer API interception** - Faster than HTML parsing
3. **Limit concurrency** - Playwright uses more resources
4. **Close pages** - Free memory after parsing
5. **Use headless mode** - Much faster than headed

## Troubleshooting

See the [Troubleshooting section](docs/playwright_spider_guide.md#troubleshooting) in the full guide.

Quick fixes:
- **Timeout errors**: Increase `wait_for_timeout` or check selector
- **Bot detected**: Enable stealth mode, check user agent rotation
- **No API captured**: Verify patterns match (check browser DevTools)
- **Memory issues**: Reduce `CONCURRENT_REQUESTS` in settings

---

For more details, see: `docs/playwright_spider_guide.md`
