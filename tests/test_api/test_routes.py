"""Unit tests for API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from api.routes import dashboard as dashboard_routes
from data_models import Product, JobListing


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestProductRoutes:
    def _seed_product(self, db_session) -> Product:
        product = Product(
            title="Test Product",
            price=19.99,
            url="https://example.com/product/1",
            source="test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product

    def test_list_products_empty(self, client):
        resp = client.get("/products/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_products(self, client, db_session):
        self._seed_product(db_session)
        resp = client.get("/products/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Product"

    def test_get_product(self, client, db_session):
        product = self._seed_product(db_session)
        resp = client.get(f"/products/{product.id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Product"

    def test_get_product_not_found(self, client):
        resp = client.get("/products/999")
        assert resp.status_code == 404


class TestJobRoutes:
    def _seed_job(self, db_session) -> JobListing:
        job = JobListing(
            title="Test Job",
            company="Test Co",
            url="https://example.com/job/1",
            source="test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    def test_list_jobs_empty(self, client):
        resp = client.get("/jobs/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_jobs(self, client, db_session):
        self._seed_job(db_session)
        resp = client.get("/jobs/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_job_not_found(self, client):
        resp = client.get("/jobs/999")
        assert resp.status_code == 404


class TestAnalyticsRoute:
    def test_analytics_empty(self, client):
        resp = client.get("/analytics/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_products"] == 0
        assert data["total_jobs"] == 0


class TestDashboardRawScrape:
    def test_raw_scrape_page_loads(self, client):
        resp = client.get("/dashboard/raw-scrape")
        assert resp.status_code == 200
        assert "Manual Raw Scrape" in resp.text

    def test_raw_scrape_result_renders(self, client, monkeypatch):
        def _fake_run_raw_scrape(spider: str, url: str | None, max_items: int):
            return {
                "ok": True,
                "file": "data/raw/products_raw_20260317T100000Z.json",
                "count": 1,
                "preview": [{"title": "Book A", "source": "test"}],
            }

        monkeypatch.setattr(dashboard_routes, "_run_raw_scrape", _fake_run_raw_scrape)
        resp = client.post(
            "/dashboard/raw-scrape",
            data={"spider": "products", "url": "", "preview_limit": "5"},
        )

        assert resp.status_code == 200
        assert "Saved 1 raw items." in resp.text
        assert "products_raw_20260317T100000Z.json" in resp.text
