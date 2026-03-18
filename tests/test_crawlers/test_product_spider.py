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

WOOCOMMERCE_LISTING_HTML = """
<html>
<body>
  <ul class="products">
    <li class="product">
      <a class="woocommerce-LoopProduct-link" href="https://anix.lk/product/demo-watch/">
        <h2 class="woocommerce-loop-product__title">Demo Watch</h2>
      </a>
      <span class="price">
        <ins>
          <span class="woocommerce-Price-amount amount">
            <bdi><span class="woocommerce-Price-currencySymbol">Rs</span>&nbsp;12,999.00</bdi>
          </span>
        </ins>
      </span>
      <img src="https://anix.lk/wp-content/demo-watch-200x230.png" />
    </li>
  </ul>
</body>
</html>
"""

PRODUCT_DETAIL_WITH_RELATED_HTML = """
<html>
<head>
  <meta property="og:title" content="Detail Watch" />
  <meta property="product:price:amount" content="15999" />
  <meta property="og:image" content="https://anix.lk/wp-content/detail-watch.png" />
</head>
<body class="single-product">
  <div class="product type-product"></div>
  <ul class="products">
    <li class="product">
      <a class="woocommerce-LoopProduct-link" href="https://anix.lk/product/related-watch/">
        <h2 class="woocommerce-loop-product__title">Related Watch</h2>
      </a>
      <span class="price"></span>
    </li>
  </ul>
</body>
</html>
"""


def _fake_response(url: str = "https://books.toscrape.com/catalogue/page-1.html") -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, request=request, body=SAMPLE_HTML.encode("utf-8"))


def _fake_response_with_html(url: str, html: str) -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, request=request, body=html.encode("utf-8"))


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

    def test_parse_woocommerce_extracts_nested_price_text(self):
        spider = ProductSpider()
        response = _fake_response_with_html(
            url="https://anix.lk/shop/",
            html=WOOCOMMERCE_LISTING_HTML,
        )

        items = [i for i in spider.parse(response) if isinstance(i, dict)]

        assert len(items) == 1
        assert items[0]["title"] == "Demo Watch"
        assert "12,999.00" in items[0]["price"]

    def test_parse_product_detail_prefers_detail_price_over_related_grid(self):
        spider = ProductSpider()
        response = _fake_response_with_html(
            url="https://anix.lk/product/detail-watch/",
            html=PRODUCT_DETAIL_WITH_RELATED_HTML,
        )

        items = [i for i in spider.parse(response) if isinstance(i, dict)]

        assert len(items) == 1
        assert items[0]["title"] == "Detail Watch"
        assert items[0]["price"] == "15999"
        assert items[0]["url"] == "https://anix.lk/product/detail-watch/"
