from __future__ import annotations

import math
import threading
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, create_engine, select, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload, sessionmaker

from .db.models import Article, ArticleImage, ArticleVideo
from .errors import CrawlError
from .runtime import Deadline
from .settings import Settings


def _duplicate_article(exc: IntegrityError) -> bool:
    original = exc.orig
    code = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    name = getattr(getattr(original, "diag", None), "constraint_name", None)
    if code == "23505":
        return name in ("articles_url_key", "articles_pkey")
    message = str(original).lower()
    return "unique constraint failed" in message and ("articles.url" in message or "articles.id" in message)


class ArticleRepository:
    """Service-owned DB connection, initialized only on an explicit save request."""

    def __init__(self, settings: Settings, *, session_factory=None):
        self.settings = settings
        self._factory = session_factory
        self._engine = None
        self._lock = threading.Lock()

    def _session(self):
        with self._lock:
            if self._factory is None:
                if not self.settings.database_url:
                    raise CrawlError("DB_UNAVAILABLE", "DATABASE_URL is required when save_to_db=true.", 503)
                if not self.settings.database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
                    raise CrawlError("DB_UNAVAILABLE", "DATABASE_URL must use PostgreSQL with psycopg2.", 503)
                self._engine = create_engine(
                    self.settings.database_url, pool_pre_ping=True,
                    pool_size=self.settings.max_concurrent_crawls, max_overflow=0,
                    pool_timeout=min(self.settings.connect_timeout, self.settings.crawl_timeout),
                    connect_args={
                        "connect_timeout": max(1, math.ceil(self.settings.connect_timeout)),
                        "application_name": self.settings.db_application_name,
                    },
                )
                self._factory = sessionmaker(self._engine, expire_on_commit=False)
        return self._factory()

    @staticmethod
    def _budget(session, deadline: Deadline):
        remaining_ms = str(max(1, int(deadline.remaining() * 1000)))
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("SELECT set_config('statement_timeout', :ms, true), set_config('lock_timeout', :ms, true)"), {"ms": remaining_ms})

    @staticmethod
    def _find(session, url):
        return session.scalar(select(Article).where(Article.url == url).options(selectinload(Article.images), selectinload(Article.videos)))

    @staticmethod
    def _snapshot(article):
        def row(instance):
            return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}
        return {"articles": [row(article)], "article_images": [row(image) for image in article.images], "article_videos": [row(video) for video in article.videos]}

    def find(self, url: str, deadline: Deadline):
        try:
            with self._session() as session:
                self._budget(session, deadline)
                article = self._find(session, url)
                deadline.remaining()
                return self._snapshot(article) if article else None
        except SQLAlchemyError:
            raise CrawlError("DB_UNAVAILABLE", "Could not read the article database.", 503, retryable=True) from None

    def _values(self, model, row):
        result = dict(row)
        for column in model.__table__.columns:
            value = result.get(column.name)
            if value is None:
                continue
            if isinstance(column.type, UUID) and isinstance(value, str):
                result[column.name] = uuid.UUID(value)
            elif isinstance(column.type, DateTime) and isinstance(value, str):
                value = datetime.fromisoformat(value)
                if value.tzinfo:
                    value = value.astimezone(ZoneInfo(self.settings.record_timezone)).replace(tzinfo=None)
                result[column.name] = value
        return result

    def save(self, data, deadline: Deadline):
        url = data["articles"][0]["url"]
        try:
            with self._session() as session:
                self._budget(session, deadline)
                existing = self._find(session, url)
                if existing:
                    deadline.remaining()
                    return self._snapshot(existing), "existing"
                article = Article(**self._values(Article, data["articles"][0]))
                article.images = [ArticleImage(**self._values(ArticleImage, row)) for row in data["article_images"]]
                article.videos = [ArticleVideo(**self._values(ArticleVideo, row)) for row in data["article_videos"]]
                session.add(article)
                deadline.remaining()
                session.flush()
                deadline.remaining()
                result = self._snapshot(article)
                session.commit()
                return result, "created"
        except IntegrityError as exc:
            if _duplicate_article(exc):
                existing = self.find(url, deadline)
                if existing:
                    return existing, "existing"
            raise CrawlError("DB_UNAVAILABLE", "Could not save the article and its media.", 503, retryable=True) from None
        except SQLAlchemyError:
            raise CrawlError("DB_UNAVAILABLE", "Could not save the article and its media.", 503, retryable=True) from None

    def close(self):
        if self._engine is not None:
            self._engine.dispose()
