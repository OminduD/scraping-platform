"""Unit tests for the transform pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from scrapy.exceptions import DropItem

from pipelines.transform.cleaner import TransformPipeline, _parse_price


class TestParsePrice:
    def test_pound_sign(self):
        assert _parse_price("£25.89") == 25.89

    def test_dollar_sign(self):
        assert _parse_price("$1,200.00") == 1200.00

    def test_plain_number(self):
        assert _parse_price("42.5") == 42.5

    def test_no_match(self):
        assert _parse_price("free") is None

    def test_empty(self):
        assert _parse_price("") is None


class TestTransformPipeline:
    def setup_method(self):
        self.pipeline = TransformPipeline()
        self.spider = MagicMock()
        self.spider.name = "test"
        self.pipeline.open_spider(self.spider)

    def test_strips_whitespace(self):
        item = {"title": "  Hello World  ", "url": "https://example.com/1"}
        result = self.pipeline.process_item(item, self.spider)
        assert result["title"] == "Hello World"

    def test_parses_price_string(self):
        item = {"price": "£25.89", "url": "https://example.com/2"}
        result = self.pipeline.process_item(item, self.spider)
        assert result["price"] == 25.89

    def test_drops_duplicate_url(self):
        item1 = {"url": "https://example.com/dup"}
        item2 = {"url": "https://example.com/dup"}
        self.pipeline.process_item(item1, self.spider)
        with pytest.raises(DropItem):
            self.pipeline.process_item(item2, self.spider)

    def test_normalizes_source(self):
        item = {"source": "BOOKS.TOSCRAPE.COM", "url": "https://example.com/3"}
        result = self.pipeline.process_item(item, self.spider)
        assert result["source"] == "books.toscrape.com"
