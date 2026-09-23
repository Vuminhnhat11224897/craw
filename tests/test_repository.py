import unittest
import uuid
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from craw_real_times.article_crawler import ParsedArticle
from craw_real_times.config.base import SiteConfig
from craw_real_times.db.models import Base, Article, ArticleImage
from craw_real_times.repository import ArticleRepository
from craw_real_times.runtime import Deadline
from craw_real_times.serializers import build_article_export
from craw_real_times.settings import Settings


@compiles(JSONB, "sqlite")
def compile_jsonb_for_test(type_, compiler, **kw):
    return "JSON"


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        self.repository = ArticleRepository(Settings(), session_factory=self.factory)
        parsed = ParsedArticle("https://example.com/a", "Title", None, "Content", None, None, (), None, ["https://cdn.example.com/a.jpg"], [])
        self.export = build_article_export(parsed, site=SiteConfig(key="example", base_url="https://example.com"), request_id="test", article_namespace=uuid.NAMESPACE_URL)

    def tearDown(self):
        self.engine.dispose()

    def test_persists_same_ids_timestamps_and_foreign_keys_as_export(self):
        data, status = self.repository.save(self.export["data"], Deadline(5))
        self.assertEqual(status, "created")
        with self.factory() as session:
            article = session.scalar(select(Article))
            image = session.scalar(select(ArticleImage))
            self.assertEqual(str(article.id), self.export["data"]["articles"][0]["id"])
            self.assertEqual(article.created_at, datetime.fromisoformat(self.export["data"]["articles"][0]["created_at"]))
            self.assertEqual(str(image.id), self.export["data"]["article_images"][0]["id"])
            self.assertEqual(image.article_id, article.id)

    def test_existing_url_returns_stored_article_without_replacing_it(self):
        self.repository.save(self.export["data"], Deadline(5))
        self.export["data"]["articles"][0]["title"] = "Changed title"
        data, status = self.repository.save(self.export["data"], Deadline(5))
        self.assertEqual(status, "existing")
        self.assertEqual(data["articles"][0]["title"], "Title")
