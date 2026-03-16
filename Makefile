.PHONY: help install dev lint test up down logs migrate seed crawl api worker

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Local development ────────────────────────────────

install: ## Install production dependencies
	pip install -r requirements.txt
	playwright install chromium

dev: ## Install development dependencies
	pip install -e ".[dev]"
	playwright install chromium

lint: ## Run linter
	ruff check .
	mypy data_models api

test: ## Run tests
	pytest -v --cov=crawlers --cov=pipelines --cov=api --cov-report=term-missing

# ── Docker ───────────────────────────────────────────

up: ## Start all services
	docker compose up -d --build

down: ## Stop all services
	docker compose down -v

logs: ## Tail service logs
	docker compose logs -f

# ── Database ─────────────────────────────────────────

migrate: ## Run database migrations
	alembic upgrade head

seed: ## Seed database with sample data
	python scripts/seed_db.py

# ── Scraping ─────────────────────────────────────────

crawl: ## Launch a crawl (usage: make crawl SPIDER=products)
	python -m scripts.run_spider $(SPIDER)

api: ## Run API server locally
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

worker: ## Run a worker process
	python -m infrastructure.workers.worker
