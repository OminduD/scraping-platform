"""Unit tests for the product spider."""

from __future__ import annotations

from scrapy.http import HtmlResponse, Request

from crawlers.ecommerce.product_spider import ProductSpider


SAMPLE_HTML = """
<html>
<body>
<ol class="row">
  <article class="product_pod">
    <h3><a href="catalogue/book-one_1/index.html" title="Book One">Book One</a></h3>
    <p class="price_color">£25.89</p>
    <p class="availability">In stock</p>
    <p class="star-rating Three"></p>
  </article>
  <article class="product_pod">
    <h3><a href="catalogue/book-two_2/index.html" title="Book Two">Book Two</a></h3>
    <p class="price_color">£12.00</p>
    <p class="availability">In stock</p>
    <p class="star-rating Five"></p>
  </article>
</ol>
</body>
</html>
"""


def _fake_response(url: str = "https://books.toscrape.com/catalogue/page-1.html") -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, request=request, body=SAMPLE_HTML.encode("utf-8"))


class TestProductSpider:
    def test_parse_extracts_products(self):
        spider = ProductSpider()
        response = _fake_response()
        items = list(spider.parse(response))

        products = [i for i in items if isinstance(i, dict)]
        assert len(products) == 2

    def test_parse_fields(self):
        spider = ProductSpider()
        response = _fake_response()
        items = [i for i in spider.parse(response) if isinstance(i, dict)]

        first = items[0]
        assert first["title"] == "Book One"
        assert first["price"] == "£25.89"
        assert first["source"] == "books.toscrape.com"
        assert first["rating"] == "Three"

    def test_parse_follows_pagination(self):
        html_with_next = SAMPLE_HTML.replace("</body>", """
        <li class="next"><a href="page-2.html">next</a></li>
        </body>""")
        request = Request(url="https://books.toscrape.com/catalogue/page-1.html")
        response = HtmlResponse(
            url="https://books.toscrape.com/catalogue/page-1.html",
            request=request,
            body=html_with_next.encode("utf-8"),
        )
        spider = ProductSpider()
        results = list(spider.parse(response))
        requests = [r for r in results if isinstance(r, Request)]
        assert len(requests) == 1
        assert "page-2.html" in requests[0].url
