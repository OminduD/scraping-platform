"""Unit tests for the job spider."""

from __future__ import annotations

from scrapy.http import HtmlResponse, Request

from crawlers.jobs.job_spider import JobSpider


SAMPLE_HTML = """
<html>
<body>
<div class="card-content">
  <h2 class="title">Senior Python Developer</h2>
  <h3 class="company">Acme Corp</h3>
  <p class="location">Remote</p>
  <time datetime="2024-01-15">Jan 15</time>
  <a href="/jobs/123">Apply</a>
</div>
<div class="card-content">
  <h2 class="title">Data Engineer</h2>
  <h3 class="company">DataCo</h3>
  <p class="location">New York, NY</p>
  <time datetime="2024-01-14">Jan 14</time>
  <a href="/jobs/456">Apply</a>
</div>
</body>
</html>
"""


def _fake_response(url: str = "https://realpython.github.io/fake-jobs/") -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, request=request, body=SAMPLE_HTML.encode("utf-8"))


class TestJobSpider:
    def test_parse_extracts_jobs(self):
        spider = JobSpider()
        items = list(spider.parse(_fake_response()))
        jobs = [i for i in items if isinstance(i, dict)]
        assert len(jobs) == 2

    def test_parse_fields(self):
        spider = JobSpider()
        items = [i for i in spider.parse(_fake_response()) if isinstance(i, dict)]
        first = items[0]
        assert first["title"] == "Senior Python Developer"
        assert first["company"] == "Acme Corp"
        assert first["location"] == "Remote"
