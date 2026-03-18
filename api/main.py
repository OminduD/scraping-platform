"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from prometheus_client import make_asgi_app

from api.routes import products, jobs, analytics, export, dashboard
from data_models import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (use Alembic in production)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Scraping Platform API",
    description="REST API for querying scraped product and job data.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Static files ────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Routes ───────────────────────────────────────────────────────────
# API v1 routes
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard API"])

# Legacy routes (for backwards compatibility)
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(export.router, prefix="/export", tags=["Export"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# ── Prometheus metrics endpoint ──────────────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root to static dashboard."""
    return RedirectResponse(url="/static/index.html")


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
