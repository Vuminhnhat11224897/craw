from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from craw_real_times.config.base import SiteConfig
from craw_real_times.db.models import Article, ArticleImage, ArticleVideo
from craw_real_times.article_crawler import ParsedArticle

from craw_real_times.serializers import build_article_export, encode_article_export


class ArticleExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace_patch = patch.dict(
            os.environ,
            {"ARTICLE_UUIDV5_NAMESPACE": "6ba7b811-9dad-11d1-80b4-00c04fd430c8"},
        )
        self.namespace_patch.start()
        from craw_real_times.db.models import clear_article_uuidv5_namespace_cache

        clear_article_uuidv5_namespace_cache()

    def tearDown(self) -> None:
        self.namespace_patch.stop()
        from craw_real_times.db.models import clear_article_uuidv5_namespace_cache

        clear_article_uuidv5_namespace_cache()

    def test_export_has_all_table_columns_and_connected_media_ids(self) -> None:
        article = ParsedArticle(
            url="https://example.com/news/story.html",
            title="Bài báo tiếng Việt",
            description=None,
            content="Nội dung đủ dài của bài báo.",
            category_id=None,
            category_name=None,
            tags=("Khoa học", "Công nghệ"),
            publish_date=None,
            images=("https://cdn.example.com/image.jpg",),
            videos=("https://cdn.example.com/video.mp4",),
        )

        export = build_article_export(
            article,
            site=SiteConfig(key="example", base_url="https://example.com"),
            request_id="request-test",
            now=datetime(2026, 9, 23, 10, 0, 0),
        )
        data = export["data"]

        self.assertEqual(set(data["articles"][0]), set(Article.__table__.columns.keys()))
        self.assertEqual(set(data["article_images"][0]), set(ArticleImage.__table__.columns.keys()))
        self.assertEqual(set(data["article_videos"][0]), set(ArticleVideo.__table__.columns.keys()))
        self.assertEqual(data["articles"][0]["category_id"], None)
        self.assertEqual(data["articles"][0]["tags"], "Khoa học, Công nghệ")
        article_id = data["articles"][0]["id"]
        self.assertEqual(data["article_images"][0]["article_id"], article_id)
        self.assertEqual(data["article_videos"][0]["article_id"], article_id)
        self.assertNotIn("persistence_status", export)

    def test_publish_date_is_normalized_to_vietnam_time(self) -> None:
        cases = [
            (datetime(2026, 9, 25, 10, 51), "2026-09-25T10:51:00+07:00"),
            (datetime(2026, 9, 25, 7, 0, 1, tzinfo=timezone.utc), "2026-09-25T14:00:01+07:00"),
            (
                datetime(2026, 9, 25, 14, 0, 1, tzinfo=timezone(timedelta(hours=7))),
                "2026-09-25T14:00:01+07:00",
            ),
        ]
        for publish_date, expected in cases:
            article = ParsedArticle(
                url="https://example.com/news/story.html",
                title="Bài báo",
                description=None,
                content="Nội dung.",
                category_id=None,
                category_name=None,
                tags=(),
                publish_date=publish_date,
                images=(),
                videos=(),
            )
            export = build_article_export(
                article,
                site=SiteConfig(key="example", base_url="https://example.com"),
                request_id="request-test",
            )
            self.assertEqual(export["data"]["articles"][0]["publish_date"], expected)

    def test_encode_returns_utf8_json_bytes_with_a_final_newline(self) -> None:
        encoded = encode_article_export({"title": "Bản tin tiếng Việt"})

        self.assertTrue(encoded.endswith(b"\n"))
        self.assertEqual(json.loads(encoded.decode("utf-8")), {"title": "Bản tin tiếng Việt"})


if __name__ == "__main__":
    unittest.main()
