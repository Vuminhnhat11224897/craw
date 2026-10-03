import unittest
from uuid import UUID

from craw_real_times.article_crawler import ArticleCrawler
from craw_real_times.serializers import build_article_export
from craw_real_times.site_resolver import resolve_site


class VietnamFinanceTest(unittest.TestCase):
    url = "https://vietnamfinance.vn/chung-cu-moi-tai-ha-noi-co-dang-giam-gia-d151222.html"
    title = "Chung cư mới tại Hà Nội có đang giảm giá?"
    sapo = "(VNF) - Giá bán tại một số dự án mới đã xuất hiện mức điều chỉnh."
    content = "Trên thị trường, giá chung cư đang phân hóa theo từng dự án và khả năng tài chính của người mua."
    image = "https://i.ex-cdn.com/vietnamfinance.vn/files/content/2026/09/28/chung-cu.jpg"

    def html(self):
        return f"""
            <html lang="vi"><head>
              <meta property="og:title" content="{self.title}">
              <meta name="description" content="Mô tả SEO của bài báo.">
              <meta property="article:section" content="News">
              <script type="application/ld+json">{{
                "@type": "NewsArticle", "datePublished": "2026-10-03T14:15:55+07:00"
              }}</script>
            </head><body>
              <ul class="breadcrumb"><li><a href="/bat-dong-san/">Bất động sản</a></li></ul>
              <div class="detail-content">
                <div class="none_adsgg_auto">
                  <h1 class="detail-title">{self.title}</h1>
                  <div class="detail-time-public"><strong>Ái Sa</strong> -
                    <span>03/10/2026 14:15 (GMT+7)</span>
                  </div>
                  <h2 class="detail-sapo">{self.sapo}</h2>
                </div>
                <div class="content_detailnews" id="news_detail">
                  <div id="explus-editor">
                    <p>{self.content}</p><figure><img src="{self.image}"></figure>
                    <div class="recommended-in-content">
                      <p>Bài được đề xuất không thuộc nội dung đang đọc.</p>
                      <img src="/recommended.jpg">
                    </div>
                    <div class="lazy_adv"><p>Thông điệp thương hiệu.</p><img src="/ad.jpg"></div>
                  </div>
                </div>
              </div>
              <div class="article__content"><p>{'Tin khác. ' * 100}</p><img src="/sidebar.jpg"></div>
            </body></html>
        """

    def crawl(self, html):
        class Client:
            def get(self, requested_url):
                return html

        site = resolve_site(self.url)
        return ArticleCrawler(site, client=Client()).fetch_article(self.url)

    def test_exports_body_and_images_without_recommendations_or_advertising(self):
        html = self.html()
        layouts = {
            "news_detail": html,
            "content_detailnews": html.replace('id="news_detail"', ''),
            "explus-editor": html.replace('id="news_detail"', '').replace('class="content_detailnews"', ''),
        }
        for layout, markup in layouts.items():
            with self.subTest(layout=layout):
                parsed = self.crawl(markup)
                result = build_article_export(
                    parsed, site=resolve_site(self.url), request_id="test",
                    article_namespace=UUID(int=0),
                )
                article = result["data"]["articles"][0]
                self.assertEqual(article["content"], self.content)
                self.assertEqual(article["category_id"], "bat-dong-san")
                self.assertEqual(article["category_name"], "Bất động sản")
                self.assertEqual(article["publish_date"], "2026-10-03T14:15:55+07:00")
                self.assertEqual(article["article_name"], "vietnamfinance")
                self.assertEqual(
                    [image["image_path"] for image in result["data"]["article_images"]],
                    [self.image],
                )
                self.assertEqual(result["data"]["article_videos"], [])

    def test_prefers_visible_title_and_sapo_over_seo_metadata(self):
        html = self.html().replace(
            f'property="og:title" content="{self.title}"',
            'property="og:title" content="Tiêu đề SEO cũ"',
        )
        parsed = self.crawl(html)
        self.assertEqual(parsed.title, self.title)
        self.assertEqual(parsed.description, self.sapo)

    def test_uses_metadata_when_visible_title_and_sapo_are_missing(self):
        html = self.html().replace(f'<h1 class="detail-title">{self.title}</h1>', '')
        html = html.replace(f'<h2 class="detail-sapo">{self.sapo}</h2>', '')
        parsed = self.crawl(html)
        self.assertEqual(parsed.title, self.title)
        self.assertEqual(parsed.description, "Mô tả SEO của bài báo.")

    def test_excludes_caption_text_but_keeps_image_and_body(self):
        caption = "Lịch sử California Fitness có nhiều lần đổi chủ. Ảnh: California Fitness"
        ending = "Thương hiệu đang hoạt động tại Việt Nam thuộc một pháp nhân riêng biệt."
        for caption_html in [caption, f'<p>{caption}</p>']:
            with self.subTest(caption_html=caption_html):
                html = self.html().replace(
                    f'<p>{self.content}</p><figure><img src="{self.image}"></figure>',
                    f'<p>{self.content}</p><figure><img src="{self.image}">'
                    f'<figcaption class="js">{caption_html}</figcaption></figure><p>{ending}</p>',
                )
                parsed = self.crawl(html)
                self.assertEqual(parsed.content, "\n\n".join([self.content, ending]))
                self.assertEqual(parsed.images, [self.image])

    def test_keeps_nested_paragraphs_in_document_order(self):
        nested = "Đây là đoạn nằm trong khối nội dung lồng nhau, cần được giữ đúng thứ tự."
        ending = "Đây là đoạn kết luận của bài viết, phải nằm sau đoạn nội dung lồng nhau."
        html = self.html().replace(
            f'<p>{self.content}</p>',
            f'<p>{self.content}</p><div><p>{nested}</p></div><p>{ending}</p>',
        )
        self.assertEqual(self.crawl(html).content, "\n\n".join([self.content, nested, ending]))

    def test_keeps_editorial_paragraphs_that_discuss_advertising(self):
        editorial = "Doanh thu quảng cáo tăng trong năm nay, theo báo cáo tài chính của doanh nghiệp."
        html = self.html().replace(f'<p>{self.content}</p>', f'<p>{self.content}</p><p>{editorial}</p>')
        self.assertEqual(self.crawl(html).content, "\n\n".join([self.content, editorial]))

    def test_reads_sapo_rendered_as_h3(self):
        html = self.html().replace(
            f'<h2 class="detail-sapo">{self.sapo}</h2>',
            f'<h3 class="detail-sapo">{self.sapo}</h3>',
        )
        self.assertEqual(self.crawl(html).description, self.sapo)


if __name__ == "__main__":
    unittest.main()
