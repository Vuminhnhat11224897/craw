from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from craw_real_times.config.base import SiteConfig
from craw_real_times.db.models import (
    Article,
    ArticleImage,
    ArticleVideo,
    article_id_from_url,
    generate_uuid7,
)
from craw_real_times.article_crawler import ArticleCrawler, ParsedArticle
from craw_real_times.settings import Settings


def _field_value(value: Any) -> Any:
    if isinstance(value, (datetime, uuid.UUID)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    return value


def _record_time(now: datetime, timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    if now.tzinfo is None:
        now = now.replace(tzinfo=zone)
    return now.astimezone(zone).replace(tzinfo=None)


def _to_record_timezone(value: datetime | None, timezone_name: str) -> datetime | None:
    if value is None:
        return None
    zone = ZoneInfo(timezone_name)
    # Sites without an explicit offset publish local Vietnam time.
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def build_article_export(
    parsed: ParsedArticle,
    *,
    site: SiteConfig,
    request_id: str,
    now: datetime | None = None,
    record_timezone: str = "Asia/Ho_Chi_Minh",
    article_namespace: uuid.UUID | None = None,
    max_videos_per_article: int = Settings.max_videos_per_article,
    image_records: Sequence[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Create a JSON-ready export with every column in the three DB tables."""
    exported_at = now or datetime.now(timezone.utc)
    record_timestamp = _record_time(exported_at, record_timezone)
    if not parsed.url or len(parsed.url) > 2000:
        raise ValueError("Article URL must be non-empty and no longer than 2000 characters.")
    article_id = article_id_from_url(parsed.url, article_namespace)
    title = ArticleCrawler._trim_to_column_length(parsed.title, Article.title)
    url = ArticleCrawler._trim_to_column_length(parsed.url, Article.url)
    if not title or not url:
        raise ValueError("Article title and URL must be non-empty.")

    article_row = {
        "id": str(article_id),
        "title": title,
        "description": parsed.description,
        "content": parsed.content,
        "category_id": ArticleCrawler._trim_to_column_length(parsed.category_id, Article.category_id),
        "category_name": ArticleCrawler._trim_to_column_length(parsed.category_name, Article.category_name),
        "comments": None,
        "tags": ArticleCrawler._trim_to_column_length(
            ArticleCrawler._join_tags(parsed.tags), Article.tags
        ),
        "url": url,
        "publish_date": _field_value(_to_record_timezone(parsed.publish_date, record_timezone)),
        "created_at": record_timestamp.isoformat(),
        "updated_at": record_timestamp.isoformat(),
        "article_name": ArticleCrawler._trim_to_column_length(
            site.resolved_article_name(), Article.article_name
        ),
    }

    images: list[dict[str, Any]] = []
    if image_records is None:
        image_records = [(url, "pending") for url in parsed.images]
    for sequence_number, (image_path, status) in enumerate(image_records, start=1):
        image_path = ArticleCrawler._trim_to_column_length(image_path, ArticleImage.image_path)
        if image_path:
            images.append({
                "id": str(generate_uuid7()),
                "article_id": str(article_id),
                "image_path": image_path,
                "status": status,
                "sequence_number": sequence_number,
                "created_at": record_timestamp.isoformat(),
            })

    videos: list[dict[str, Any]] = []
    for sequence_number, video_path in enumerate(parsed.videos[:max_videos_per_article], start=1):
        video_path = ArticleCrawler._trim_to_column_length(video_path, ArticleVideo.video_path)
        if video_path:
            videos.append({
                "id": str(generate_uuid7()),
                "article_id": str(article_id),
                "video_path": video_path,
                "sequence_number": sequence_number,
                "created_at": record_timestamp.isoformat(),
            })

    exported_at_utc = exported_at.astimezone(timezone.utc) if exported_at.tzinfo else exported_at.replace(
        tzinfo=ZoneInfo(record_timezone)
    ).astimezone(timezone.utc)
    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "status": "success",
        "exported_at": exported_at_utc.isoformat().replace("+00:00", "Z"),
        "generated_timestamp_timezone": record_timezone,
        "duration_ms": 0,
        "data": {
            "articles": [article_row],
            "article_images": images,
            "article_videos": videos,
        },
        "warnings": [],
    }


def encode_article_export(export: Mapping[str, Any]) -> bytes:
    return (json.dumps(export, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
