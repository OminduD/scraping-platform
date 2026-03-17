"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from api.routes import products, jobs, analytics, export
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

# ── Routes ───────────────────────────────────────────────────────────
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(export.router, prefix="/export", tags=["Export"])

# ── Prometheus metrics endpoint ──────────────────────────────────────
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
