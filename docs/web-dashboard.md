# Web Dashboard

The scraping platform includes an interactive web dashboard for managing scrapes and exporting data.

**Access:** http://localhost:8000 (redirects to `/static/index.html`)

## Pages

### Home Dashboard

**URL:** `/static/index.html`

**Features:**
- View total product and job counts
- See recent products and jobs in tables
- Export entire database to CSV, TSV, PSV, or HTML
- Images displayed inline
- URLs are clickable hyperlinks

**Tables:**
- Product table shows: Image, Title, Price, Source, Link
- Job table shows: Title, Company, Location, Source, Link

**Export buttons:**
```
GET /export/products/csv
GET /export/products/tsv
GET /export/products/psv
GET /export/products/html

GET /export/jobs/csv
GET /export/jobs/tsv
GET /export/jobs/psv
GET /export/jobs/html
```

### Raw Scrape

**URL:** `/static/raw-scrape.html`

**Purpose:** Run manual scrapes without database processing. Saves raw JSON to `data/raw/`.

**Form Fields:**
- **Spider** — Select `products` or `jobs`
- **URL** — Optional custom URL (uses spider default if empty)
- **Preview Limit** — Number of items to preview (1-100, default 10)

**Output:**
- Raw JSON saved to `data/raw/{spider}_raw_{timestamp}.json`
- Preview table with first N items
- Export buttons for CSV, TSV, PSV, HTML
- "Load to PostgreSQL" button

**API Endpoint:**
```
POST /api/v1/raw-scrape
Content-Type: multipart/form-data

spider=products&url=https://example.com&preview_limit=10
```

**Response:**
```json
{
  "ok": true,
  "file": "data/raw/products_raw_20260318T103000Z.json",
  "count": 50,
  "preview": [
    {
      "title": "Product Name",
      "price": "$29.99",
      "url": "https://example.com/product",
      "image_url": "https://example.com/image.jpg"
    }
  ]
}
```

### Load to DB

**URL:** `/static/load-to-db.html`

**Purpose:** Browse and load raw JSON files into PostgreSQL.

**Features:**
- Lists all JSON files in `data/raw/`
- Shows file size and modification time
- Export each file to CSV/TSV/PSV
- Load file to PostgreSQL with one click

**API Endpoints:**
```
GET /api/v1/raw-files
```

Response:
```json
{
  "files": [
    {
      "name": "products_raw_20260318T103000Z.json",
      "size": 45678,
      "modified": "2026-03-18T10:30:00Z"
    }
  ]
}
```

```
POST /export/load-to-db?filename=products_raw_20260318T103000Z.json&item_type=product
```

Response:
```json
{
  "ok": true,
  "message": "Successfully loaded 50 product(s) into PostgreSQL",
  "loaded": 50,
  "file": "products_raw_20260318T103000Z.json"
}
```

## Export Formats

### CSV (Comma-Separated Values)

```
title,price,url,image_url,source
"Product Name",29.99,"https://example.com/product","https://example.com/image.jpg","example.com"
```

**MIME Type:** `text/csv`

### TSV (Tab-Separated Values)

```
title	price	url	image_url	source
Product Name	29.99	https://example.com/product	https://example.com/image.jpg	example.com
```

**MIME Type:** `text/tab-separated-values`

**Use Case:** Import into Excel, Google Sheets, data analysis tools

### PSV (Pipe-Separated Values)

```
title|price|url|image_url|source
Product Name|29.99|https://example.com/product|https://example.com/image.jpg|example.com
```

**MIME Type:** `text/plain`

**Use Case:** Compatible with Unix tools, databases that prefer pipe delimiters

### HTML

```html
<!DOCTYPE html>
<html>
<head>
  <title>Products — Scraped Results</title>
  <style>/* Styled table */</style>
</head>
<body>
  <h1>Products — Scraped Results</h1>
  <p class="meta">50 items</p>
  <table>
    <thead><tr><th>Title</th><th>Price</th>...</tr></thead>
    <tbody>...</tbody>
  </table>
</body>
</html>
```

**MIME Type:** `text/html`

**Use Case:** Viewing in browser, sharing reports

## JavaScript Utilities

**File:** `static/js/dashboard.js`

### Functions

**`renderProductsTable(items)`**
- Renders products in an HTML table
- Displays images inline
- Makes URLs clickable

**`renderJobsTable(items)`**
- Renders jobs in an HTML table
- Makes URLs clickable

**`renderRawDataTable(items)`**
- Dynamically renders any data structure
- Automatically detects image URLs
- Prioritizes common fields (image_url, title, price, url)

**`escapeHtml(text)`**
- Escapes HTML entities for safe rendering

**`truncate(str, len)`**
- Truncates long text with ellipsis

**`isUrl(str)`**
- Checks if string is a URL

## Architecture

```
┌─────────────────┐
│  Browser        │
│  (static HTML)  │
└────────┬────────┘
         │
         │ API calls (fetch)
         ▼
┌─────────────────┐
│  FastAPI        │
│  /api/v1/*      │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌──────┐  ┌──────────┐
│ JSON │  │PostgreSQL│
│ Files│  └──────────┘
└──────┘
```

- Dashboard is entirely static (HTML/CSS/JS)
- No server-side rendering
- All data loaded via JSON API calls
- Exports triggered as direct downloads

## Styling

**File:** `static/css/style.css`

**Design:**
- Clean, minimal interface
- Dark navigation bar
- Card-based layout for statistics
- Responsive tables with sticky headers
- Hover effects on rows
- Modern button styling

**Colors:**
- Background: `#f8f9fa` (light gray)
- Cards: `#fff` (white)
- Nav: `#343a40` (dark gray)
- Primary: `#0d6efd` (blue)
- Success: `#198754` (green)
- Error: `#b42318` (red)

## Benefits of Static Dashboard

1. **No template engine needed** — Simpler deployment
2. **Fast rendering** — No server-side HTML generation
3. **API-first** — Same endpoints power both UI and external clients
4. **Easy customization** — Edit HTML/CSS/JS directly
5. **Cacheable** — Static files can be CDN-cached
6. **Separation of concerns** — Frontend and backend independent

## Running Locally

```bash
# Start the API server
uvicorn api.main:app --reload

# Access dashboard
open http://localhost:8000
```

## Docker Deployment

The static files are mounted as a volume in `docker-compose.yml`:

```yaml
api:
  volumes:
    - ./static:/app/static
    - ./data:/app/data
```

This allows editing static files without rebuilding the container.
