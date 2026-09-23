import os
from functools import lru_cache
from sqlalchemy import Column, Text, String, DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid_utils
import uuid


def generate_uuid7():
    """Generate UUIDv7 and convert to standard Python UUID"""
    uuid7_obj = uuid_utils.uuid7()
    return uuid.UUID(str(uuid7_obj))


_ARTICLE_UUIDV5_NAMESPACE_ENV = "ARTICLE_UUIDV5_NAMESPACE"


@lru_cache(maxsize=1)
def _article_uuidv5_namespace() -> uuid.UUID:
    raw = os.getenv(_ARTICLE_UUIDV5_NAMESPACE_ENV)
    if not raw or not raw.strip():
        raise ValueError(f"Missing required environment variable: {_ARTICLE_UUIDV5_NAMESPACE_ENV}")
    try:
        return uuid.UUID(raw.strip())
    except Exception as exc:
        raise ValueError(
            f"Invalid UUID value for environment variable: {_ARTICLE_UUIDV5_NAMESPACE_ENV}"
        ) from exc


def clear_article_uuidv5_namespace_cache() -> None:
    _article_uuidv5_namespace.cache_clear()


def validate_article_uuidv5_namespace() -> uuid.UUID:
    """Validate configuration early so crawls fail fast before partial work."""
    return _article_uuidv5_namespace()


def article_id_from_url(url: str, namespace: uuid.UUID | None = None) -> uuid.UUID:
    """Compute a deterministic UUIDv5 for an article URL.

    The UUIDv5 name string must be the *exact* URL value that will be persisted
    in `articles.url` to preserve a stable mapping.
    """
    if url is None or not str(url).strip():
        raise ValueError("Article URL must be non-empty.")
    namespace_uuid = namespace if namespace is not None else _article_uuidv5_namespace()
    return uuid.uuid5(namespace_uuid, url)

Base = declarative_base()


class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String(1024), nullable=False, index=True)
    description = Column(Text)
    content = Column(Text)
    category_id = Column(String(100), index=True)
    category_name = Column(String(200), index=True)
    comments = Column(JSONB)
    tags = Column(String(500), index=True)
    url = Column(String(2000), unique=True, nullable=False)
    publish_date = Column(DateTime, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    article_name = Column(String(100), index=True)
    
    # Relationships
    images = relationship(
        "ArticleImage",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticleImage.sequence_number"
    )
    videos = relationship(
        "ArticleVideo",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticleVideo.sequence_number"
    )
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:30]}...', url='{self.url}')>"


class ArticleImage(Base):
    __tablename__ = 'article_images'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid7)
    article_id = Column(UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    image_path = Column(String(2000), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    sequence_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationship
    article = relationship("Article", back_populates="images")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_article_images_article_id_seq', 'article_id', 'sequence_number'),
    )
    
    def __repr__(self):
        return (
            f"<ArticleImage(id={self.id}, article_id={self.article_id}, "
            f"path='{self.image_path}', status='{self.status}')>"
        )


class ArticleVideo(Base):
    __tablename__ = 'article_videos'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid7)
    article_id = Column(UUID(as_uuid=True), ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    video_path = Column(String(4096), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationship
    article = relationship("Article", back_populates="videos")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_article_videos_article_id_seq', 'article_id', 'sequence_number'),
    )
    
    def __repr__(self):
        return f"<ArticleVideo(id={self.id}, article_id={self.article_id}, path='{self.video_path}')>"


# Helper functions for generating file paths
def generate_image_path(article_id: uuid.UUID, sequence_number: int, extension: str = "jpg") -> str:
    """Generate image path following the naming convention"""
    return f"{article_id}_img_{sequence_number}.{extension}"


def generate_video_path(article_id: uuid.UUID, sequence_number: int, extension: str = "mp4") -> str:
    """Generate video path following the naming convention"""
    return f"{article_id}_video_{sequence_number}.{extension}"


# Example usage:
