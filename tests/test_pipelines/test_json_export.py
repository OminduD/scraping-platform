"""Unit tests for the JSON export pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from pipelines.export import json_exporter
from pipelines.export.json_exporter import JsonExportPipeline


class TestJsonExportPipeline:
    def setup_method(self):
        self.pipeline = JsonExportPipeline()
        self.spider = MagicMock()
        self.spider.name = "products"

    def test_open_spider_creates_empty_json_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(json_exporter, "OUTPUT_DIR", Path(tmp_path))

        self.pipeline.open_spider(self.spider)

        assert self.pipeline.path is not None
        assert self.pipeline.path.exists()
        assert json.loads(self.pipeline.path.read_text(encoding="utf-8")) == []

    def test_checkpoint_writes_partial_results_before_close(self, tmp_path, monkeypatch):
        monkeypatch.setattr(json_exporter, "OUTPUT_DIR", Path(tmp_path))

        self.pipeline.checkpoint_every = 2
        self.pipeline.open_spider(self.spider)

        self.pipeline.process_item({"url": "https://example.com/1", "title": "One"}, self.spider)
        first_data = json.loads(self.pipeline.path.read_text(encoding="utf-8"))
        assert len(first_data) == 1
        assert first_data[0]["url"] == "https://example.com/1"

        self.pipeline.process_item({"url": "https://example.com/2", "title": "Two"}, self.spider)
        data = json.loads(self.pipeline.path.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["url"] == "https://example.com/1"
        assert data[1]["url"] == "https://example.com/2"

    def test_close_spider_writes_all_items(self, tmp_path, monkeypatch):
        monkeypatch.setattr(json_exporter, "OUTPUT_DIR", Path(tmp_path))

        self.pipeline.open_spider(self.spider)
        self.pipeline.process_item({"url": "https://example.com/1", "title": "One"}, self.spider)
        self.pipeline.process_item({"url": "https://example.com/2", "title": "Two"}, self.spider)

        self.pipeline.close_spider(self.spider)

        data = json.loads(self.pipeline.path.read_text(encoding="utf-8"))
        assert len(data) == 2
