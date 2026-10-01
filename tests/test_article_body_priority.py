import unittest

from craw_real_times.extractor.article import ArticleExtractor
from craw_real_times.extractor.site_config import ArticleSiteConfig


class ArticleBodyPriorityTest(unittest.TestCase):
    def test_body_priority_and_length_fallback(self):
        content = "Đây là nội dung chính của bài báo, cần được giữ nguyên khi trích xuất."
        body = f'<p>{content}</p><img src="/body.jpg">'
        unrelated = "Nội dung không liên quan. " * 50
        sidebar = f'<div class="content-col"><p>{unrelated}</p><img src="/sidebar.jpg"></div>'
        cases = [
            ("schema body", f'<article><div itemprop="articleBody">{body}</div>'
             f'<div class="entry"><p>{unrelated}</p></div></article>{sidebar}', None),
            ("schema tokens", f'<div itemprop="text articleBody">{body}</div>{sidebar}', None),
            ("body class", f'<article><div class="article__body">{body}</div>'
             f'<div class="entry"><p>{unrelated}</p></div></article>{sidebar}', None),
            ("hyphenated body", f'<div class="article-body">{body}</div>{sidebar}', None),
            ("cms body", f'<div class="cms-body">{body}</div>{sidebar}', None),
            ("article tag", f'<article>{body}</article>{sidebar}', None),
            ("article div", f'<div class="article">{body}</div>{sidebar}', None),
            ("article section", f'<section itemtype="https://schema.org/NewsArticle">{body}</section>{sidebar}', None),
            ("site override", f'<div class="publisher-body">{body}</div>'
             f'<article itemprop="articleBody"><p>{unrelated}</p></article>{sidebar}',
             ArticleSiteConfig(main_container_selectors=(".publisher-body",))),
            ("missing override", f'<div itemprop="articleBody">{body}</div>{sidebar}',
             ArticleSiteConfig(main_container_selectors=(".missing",))),
            ("disabled ads", f'<div class="disable-ads"><div itemprop="articleBody">'
             f'{body}</div></div>{sidebar}', None),
            ("empty schema", '<div itemprop="articleBody"></div>'
             f'<div class="detail-content">{body}</div>{sidebar}', None),
            ("embedded article", f'<div class="content-detail">{body}'
             f'<article class="ck-cms-insert-news related"><p>{unrelated}</p>'
             '</article></div>', None),
            ("article card", f'<article class="card"><p>{unrelated}</p></article>'
             f'<div class="content">{body}</div>', None),
            ("excluded schema", f'<aside class="related"><div itemprop="articleBody">'
             f'<p>{unrelated}</p><img src="/related.jpg"></div></aside>'
             f'<div itemprop="articleBody">{body}</div>{sidebar}', None),
            ("multiple bodies", f'<div itemprop="articleBody"><p>Ngắn.</p></div>'
             f'<div itemprop="articleBody">{body}</div>{sidebar}', None),
            ("length fallback", '<div class="entry"><p>Ngắn.</p></div>'
             f'<div class="content">{body}</div>', None),
        ]
        for name, html, config in cases:
            with self.subTest(case=name):
                extractor = ArticleExtractor("https://example.com/news.html")
                extractor.site_config = config
                data = extractor.extract(html)
                self.assertEqual(data.content, content)
                self.assertEqual(data.images, ["https://example.com/body.jpg"])


if __name__ == "__main__":
    unittest.main()
