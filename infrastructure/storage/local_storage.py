"""Local file storage for raw and processed HTML / JSON.

In production this can be swapped for S3-compatible object storage by
implementing the same interface.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from configs import get_settings

logger = structlog.get_logger(__name__)


class LocalStorage:
    """Stores files on the local filesystem under data/raw and data/processed."""

    def __init__(self) -> None:
        settings = get_settings().app
        self.raw_dir = Path(settings.raw_data_dir)
        self.processed_dir = Path(settings.processed_data_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def save_raw_html(self, url: str, html: str | bytes) -> Path:
        """Persist a raw HTML page to disk, keyed by URL hash."""
        filename = self._url_to_filename(url, ext=".html")
        path = self.raw_dir / filename
        content = html if isinstance(html, bytes) else html.encode("utf-8")
        path.write_bytes(content)
        logger.debug("storage.saved_raw", path=str(path))
        return path

    def save_processed(self, url: str, data: dict[str, Any]) -> Path:
        """Persist a processed JSON record to disk."""
        filename = self._url_to_filename(url, ext=".json")
        path = self.processed_dir / filename
        path.write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2))
        logger.debug("storage.saved_processed", path=str(path))
        return path

    def read_raw(self, url: str) -> str | None:
        """Read a previously saved raw HTML file."""
        path = self.raw_dir / self._url_to_filename(url, ext=".html")
        if path.exists():
            return path.read_text()
        return None

    @staticmethod
    def _url_to_filename(url: str, ext: str) -> str:
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{ts}_{url_hash}{ext}"
