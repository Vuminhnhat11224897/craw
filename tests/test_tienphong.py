import unittest
from uuid import UUID
from unittest.mock import patch

from craw_real_times.article_crawler import ArticleCrawler, SkipArticle
from craw_real_times.serializers import build_article_export
from craw_real_times.site_resolver import resolve_site


class TienPhongTest(unittest.TestCase):
    def test_crawl_uses_article_body_instead_of_larger_related_column(self):
        url = "https://tienphong.vn/suat-an-post1879994.tpo"
        content = "Nhà trường theo dõi sức khỏe học sinh sau phản ánh suất ăn có dấu hiệu bất thường."
        related = "Tin cùng chuyên mục không thuộc nội dung bài báo. " * 20
        html = f"""
            <html lang="vi"><head>
              <meta property="og:title" content="Suất ăn học sinh">
              <meta name="description" content="Mô tả SEO">
              <meta property="article:section" content="Giáo dục">
              <meta property="article:published_time" content="2026-09-27T15:58:10+07:00">
            </head><body>
              <div class="article">
                <div class="article__sapo"><p>Sapo của bài báo.</p></div>
                <div class="article__body cms-body" itemprop="articleBody">
                  <p>{content}</p><figure><img src="/school.jpg"></figure>
                </div>
              </div>
              <div class="main-col content-col"><h2>Cùng chuyên mục</h2>
                <p>{related}</p><img src="/related.jpg">
              </div>
            </body></html>
        """

        class Client:
            def get(self, requested_url):
                return html

        site = resolve_site(url)
        parsed = ArticleCrawler(site, client=Client()).fetch_article(url)
        result = build_article_export(parsed, site=site, request_id="test",
                                      article_namespace=UUID(int=0))
        article = result["data"]["articles"][0]
        self.assertEqual(article["title"], "Suất ăn học sinh")
        self.assertEqual(article["content"], content)
        self.assertEqual(article["description"], "Sapo của bài báo.")
        self.assertEqual(article["category_name"], "Giáo dục")
        self.assertEqual(article["publish_date"], "2026-09-27T15:58:10+07:00")
        self.assertEqual([image["image_path"] for image in result["data"]["article_images"]],
                         ["https://tienphong.vn/school.jpg"])

        # The shared fallback must work even without the Tiền Phong override.
        with patch("craw_real_times.extractor.article.get_article_site_config", return_value=None):
            parsed = ArticleCrawler(site, client=Client()).fetch_article(url)
        self.assertEqual(parsed.content, content)
        self.assertEqual(parsed.images, ["https://tienphong.vn/school.jpg"])

        # Secondary fallbacks must not escape the selected body either.
        html += f'<article class="card"><p>{related}</p><img src="/card.jpg"></article>'
        original_html = html
        html = html.replace('<img src="/school.jpg">', '')
        parsed = ArticleCrawler(site, client=Client()).fetch_article(url)
        self.assertEqual(parsed.content, content)
        self.assertEqual(parsed.images, [])
        html = original_html.replace(f'<p>{content}</p>', '')
        with self.assertRaises(SkipArticle):
            ArticleCrawler(site, client=Client()).fetch_article(url)

        # A video-only article still exports its own sapo and video URL.
        html = original_html.replace(f'<p>{content}</p>', '<video><source src="/news.mp4"></video>')
        html = html.replace('Sapo của bài báo.', content)
        parsed = ArticleCrawler(site, client=Client()).fetch_article(url)
        self.assertEqual(parsed.content, content)
        self.assertEqual(parsed.videos, ["https://tienphong.vn/news.mp4"])


if __name__ == "__main__":
    unittest.main()
