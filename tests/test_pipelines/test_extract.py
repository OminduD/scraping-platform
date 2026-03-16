"""Unit tests for the HTML extraction pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

from pipelines.extract.html_parser import HtmlCleanPipeline


class TestHtmlCleanPipeline:
    def setup_method(self):
        self.pipeline = HtmlCleanPipeline()
        self.spider = MagicMock()
        self.spider.name = "test"

    def test_strips_html_tags(self):
        item = {
            "title": "<b>Bold Title</b>",
            "description": "<p>Some <em>description</em> here</p>",
            "url": "https://example.com",
        }
        result = self.pipeline.process_item(item, self.spider)
        assert result["title"] == "Bold Title"
        assert result["description"] == "Some description here"

    def test_leaves_plain_text_alone(self):
        item = {"title": "Plain Title", "url": "https://example.com"}
        result = self.pipeline.process_item(item, self.spider)
        assert result["title"] == "Plain Title"

    def test_collapses_whitespace(self):
        item = {
            "description": "<p>Multiple   \n  spaces</p>",
            "url": "https://example.com",
        }
        result = self.pipeline.process_item(item, self.spider)
        assert result["description"] == "Multiple spaces"
