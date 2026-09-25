from __future__ import annotations

import unittest
from unittest.mock import Mock

from craw_real_times.config.base import SiteConfig
from craw_real_times.article_crawler import ArticleCrawler, SkipArticle
from craw_real_times.errors import CrawlError


class _FakeArticleClient:
    def __init__(self, html: str) -> None:
        self.html = html
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        return self.html


class FetchArticleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.url = "https://example.com/news/story-123.html"
        self.client = _FakeArticleClient(
            """
            <html lang="vi"><head>
              <meta property="og:title" content="Bài thử">
              <meta property="og:description" content="Mô tả thử">
            </head><body><article>
              <p>Nội dung bài báo đủ dài để được nhận diện là bài viết đầy đủ.</p>
              <p>Đoạn nội dung tiếp tục thêm thông tin cho bài báo thử nghiệm.</p>
            </article></body></html>
            """
        )
        self.crawler = ArticleCrawler(
            SiteConfig(key="example", base_url="https://example.com"),
            client=self.client,
        )

    def test_fetches_single_article_without_discovering_categories_or_database(self) -> None:
        self.crawler._discover_categories = Mock(side_effect=AssertionError("must not discover"))

        article = self.crawler.fetch_article(self.url)

        self.assertEqual(self.client.requested, [self.url])
        self.assertEqual(article.title, "Bài thử")
        self.assertIn("Nội dung bài báo", article.content or "")
        self.assertIsNone(article.category_id)
        self.assertIsNone(article.category_name)

    def test_skips_a_page_without_article_content(self) -> None:
        self.client.html = "<html><head><title>Trang thông báo</title></head><body></body></html>"

        with self.assertRaises(SkipArticle):
            self.crawler.fetch_article(self.url)

    def test_home_page_url_is_not_an_article(self) -> None:
        for url in ("https://example.com/", "https://example.com"):
            with self.assertRaises(SkipArticle):
                self.crawler.fetch_article(url)
        self.assertEqual(self.client.requested, [])

    def test_redirect_to_home_page_is_article_not_found(self) -> None:
        self.client.last_url = "https://example.com/"

        with self.assertRaises(CrawlError) as caught:
            self.crawler.fetch_article(self.url)

        self.assertEqual(caught.exception.code, "ARTICLE_NOT_FOUND")
        self.assertEqual(caught.exception.status_code, 404)

    def test_redirect_to_404_page_is_article_not_found(self) -> None:
        self.client.last_url = "https://example.com/404.html"

        with self.assertRaises(CrawlError) as caught:
            self.crawler.fetch_article(self.url)

        self.assertEqual(caught.exception.code, "ARTICLE_NOT_FOUND")

    def test_redirect_to_another_article_is_kept(self) -> None:
        self.client.last_url = "https://example.com/news/story-123-moved.html"

        article = self.crawler.fetch_article(self.url)

        self.assertEqual(article.title, "Bài thử")

    def test_tuoitre_category_from_detail_cate(self) -> None:
        url = "https://tuoitre.vn/bai-thu-100260923120510023.htm"
        client = _FakeArticleClient(
            """
            <html lang="vi"><head><meta property="og:title" content="Bài Tuổi Trẻ"></head><body>
              <div class="detail-cate"><a href="/the-gioi.htm" title="Thế giới">Thế giới</a></div>
              <article>
                <p>Nội dung bài báo đủ dài để được nhận diện là bài viết đầy đủ.</p>
                <p>Đoạn nội dung tiếp tục thêm thông tin cho bài báo thử nghiệm.</p>
              </article>
            </body></html>
            """
        )
        crawler = ArticleCrawler(SiteConfig(key="tuoitre", base_url="https://tuoitre.vn"), client=client)

        article = crawler.fetch_article(url)

        self.assertEqual(article.category_id, "the-gioi")
        self.assertEqual(article.category_name, "Thế giới")

    def test_cafef_interactive_longform(self) -> None:
        client = _FakeArticleClient(
            """
            <html lang="vi"><head>
              <meta property="og:title" content="Bài Longform CafeF">
              <meta property="og:description" content="Mô tả tóm tắt">
            </head><body>
              <div class="sp-sticky-header">
                <a class="sp-mag-logo" href="/nhom-chu-de/emagazine.chn"></a>
              </div>
              <div class="longform" id="cafef-interactive-longform">
                <header class="hero">
                  <h1>Doanh nghiệp kiến quốc</h1>
                  <p>Sapo đầu bài</p>
                </header>
                <section class="body-copy">
                  <p>Nội dung phần 1 của bài longform với đầy đủ chi tiết bằng tiếng Việt.</p>
                  <img src="https://magazine.mediacdn.vn/sample1.jpg" />
                  <p>Nội dung phần 2 mở rộng thêm thông tin phân tích thị trường kinh tế.</p>
                </section>
              </div>
            </body></html>
            """
        )
        crawler = ArticleCrawler(
            SiteConfig(key="cafef", base_url="https://cafef.vn"),
            client=client,
        )
        article = crawler.fetch_article("https://cafef.vn/bai-longform-18826092301195811.chn")
        self.assertEqual(article.title, "Bài Longform CafeF")
        self.assertIn("Nội dung phần 1", article.content or "")
        self.assertEqual(article.category_id, "emagazine")
        self.assertEqual(article.category_name, "Emagazine")
        self.assertIn("https://magazine.mediacdn.vn/sample1.jpg", article.images)


if __name__ == "__main__":
    unittest.main()
