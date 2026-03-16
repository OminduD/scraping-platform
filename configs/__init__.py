"""Shared configuration loaded from environment variables and YAML."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(name: str) -> dict:
    """Load a YAML config file from the configs/ directory."""
    path = PROJECT_ROOT / "configs" / name
    if path.exists():
        with open(path) as fh:
            return yaml.safe_load(fh) or {}
    return {}


class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    db: str = "scraping_platform"
    user: str = "scraper"
    password: str = "changeme"

    model_config = {"env_prefix": "POSTGRES_"}

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    model_config = {"env_prefix": "REDIS_"}

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class CrawlerSettings(BaseSettings):
    crawl_delay: float = 1.5
    max_retries: int = 3
    concurrent_requests: int = 8

    model_config = {"env_prefix": ""}

    def __init__(self, **kwargs):
        yaml_cfg = _load_yaml("crawler.yaml")
        merged = {**yaml_cfg, **kwargs}
        super().__init__(**merged)


class AppSettings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    log_level: str = "INFO"
    raw_data_dir: str = str(PROJECT_ROOT / "data" / "raw")
    processed_data_dir: str = str(PROJECT_ROOT / "data" / "processed")

    model_config = {"env_prefix": ""}


class Settings:
    """Aggregate settings object."""

    def __init__(self) -> None:
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.crawler = CrawlerSettings()
        self.app = AppSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
