"""Shared configuration loaded from environment variables and YAML."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(name: str) -> dict:
    """Load a YAML config file from the configs/ directory."""
    path = PROJECT_ROOT / "configs" / name
    if path.exists():
        with open(path) as fh:
            return yaml.safe_load(fh) or {}
    return {}


class _YamlSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that reads from a YAML file with lowest priority."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_file: str) -> None:
        super().__init__(settings_cls)
        self._yaml_data = _load_yaml(yaml_file)

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        val = self._yaml_data.get(field_name)
        return val, field_name, val is not None

    def __call__(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field_name in self.settings_cls.model_fields:
            val, _, is_set = self.get_field_value(None, field_name)
            if is_set:
                data[field_name] = val
        return data


class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    db: str = "scraping_platform"
    user: str = "scraper"
    password: str = "changeme"

    model_config = {"env_prefix": "POSTGRES_"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: init kwargs > env vars > YAML > field defaults
        return (
            init_settings,
            env_settings,
            _YamlSettingsSource(settings_cls, "database.yaml"),
            file_secret_settings,
        )

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
    user_agent: str = "ScrapingPlatform/1.0"
    domains: dict[str, dict] = Field(default_factory=dict)

    model_config = {"env_prefix": ""}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: init kwargs > env vars > YAML > field defaults
        return (
            init_settings,
            env_settings,
            _YamlSettingsSource(settings_cls, "crawler.yaml"),
            file_secret_settings,
        )


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
