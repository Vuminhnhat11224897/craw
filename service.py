from __future__ import annotations

import time
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
import urllib3
from minio import Minio
from minio.error import MinioException

from .article_crawler import ArticleCrawler, SkipArticle, _normalize_internal_url
from .db.models import generate_image_path
from .errors import CrawlError
from .http_client import HttpClient
from .runtime import Deadline, DomainLimiter
from .schemas import CrawlRequest
from .serializers import build_article_export
from .settings import Settings
from .site_resolver import resolve_site

IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif", "image/svg+xml": "svg", "image/bmp": "bmp", "image/tiff": "tiff"}


class CrawlService:
    def __init__(self, settings: Settings, limiter: DomainLimiter, *, client_factory=HttpClient):
        self.settings, self.limiter, self.client_factory = settings, limiter, client_factory

    def crawl(self, request: CrawlRequest, request_id: str, deadline: Deadline):
        started = time.monotonic()
        if request.download_images and not all((self.settings.minio_endpoint, self.settings.minio_access_key, self.settings.minio_secret_key)):
            raise CrawlError("MEDIA_STORAGE_NOT_CONFIGURED", "Set MINIO_ENDPOINT, MINIO_ACCESS_KEY and MINIO_SECRET_KEY to upload images.", 503)
        site = resolve_site(request.url)
        url = _normalize_internal_url(site.base_url, request.url, keep_query=site.keep_query_params)
        if not url:
            raise CrawlError("INVALID_URL", "The URL does not match this source.")

        client = self.client_factory(site, self.settings, deadline, self.limiter)
        try:
            parsed = ArticleCrawler(site, client=client, settings=self.settings).fetch_article(url)
            deadline.remaining()
            result = build_article_export(
                parsed, site=site, request_id=request_id, record_timezone=self.settings.record_timezone,
                article_namespace=uuid.UUID(self.settings.article_namespace),
                max_videos_per_article=self.settings.max_videos_per_article,
            )
            warnings = []
            if not parsed.category_id and not parsed.category_name:
                warnings.append({"code": "CATEGORY_MISSING", "message": "The article does not expose a category."})
            if request.download_images:
                result["media"] = self._save_media(result, client, site, deadline, warnings)
            result["warnings"] = warnings
            result["duration_ms"] = int((time.monotonic() - started) * 1000)
            return result
        except SkipArticle:
            raise CrawlError("NOT_AN_ARTICLE", "The URL does not contain a supported article with readable content.") from None
        except requests.Timeout:
            raise CrawlError("CRAWL_TIMEOUT", "The news source did not respond in time.", 504, retryable=True) from None
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in (404, 410):
                raise CrawlError("ARTICLE_NOT_FOUND", "The article was not found on the news source.", 404) from None
            if status == 429:
                raise CrawlError("RATE_LIMITED", "The news source is rate limiting requests.", 429, retryable=True) from None
            raise CrawlError("UPSTREAM_ERROR", "The news source rejected the crawl or returned an error.", 502, retryable=True) from None
        except requests.RequestException:
            raise CrawlError("UPSTREAM_ERROR", "Could not connect to the news source.", 502, retryable=True) from None
        finally:
            client.close()

    def _save_media(self, export, client, site, deadline, warnings):
        media = {"images_folder": None, "images_metadata": None, "videos_metadata": None}
        if export["data"]["article_images"]:
            day = datetime.now(ZoneInfo(self.settings.record_timezone)).date()
            folder = f"{day.day}_{day.month}_{day.year}"
            self._download_images(export, client, site, deadline, warnings, folder)
            media["images_folder"] = f"{self.settings.minio_endpoint.rstrip('/')}/{self.settings.minio_bucket}/{folder}"
        return media

    def _put_object(self, key, content, content_type, deadline):
        remaining = deadline.remaining()
        endpoint = urlsplit(self.settings.minio_endpoint)
        with urllib3.PoolManager(
            timeout=urllib3.Timeout(total=remaining, connect=min(self.settings.connect_timeout, remaining), read=min(self.settings.read_timeout, remaining)),
            retries=False,
        ) as http:
            storage = Minio(
                endpoint.netloc, secure=endpoint.scheme == "https",
                access_key=self.settings.minio_access_key, secret_key=self.settings.minio_secret_key,
                region=self.settings.minio_region, http_client=http,
            )
            # One bounded PUT per image; no multipart workers outliving the crawl.
            storage.put_object(self.settings.minio_bucket, key, BytesIO(content), len(content),
                               content_type=content_type, part_size=max(len(content), 5 * 1024 * 1024))
        deadline.remaining()
        return f"{self.settings.minio_endpoint.rstrip('/')}/{self.settings.minio_bucket}/{key}"

    def _download_images(self, export, client, site, deadline, warnings, folder):
        for row in export["data"]["article_images"]:
            deadline.remaining()
            source_url = row["image_path"]
            try:
                content, content_type = client.get_bytes(source_url, headers={"Referer": site.base_url})
                mime = (content_type or "").split(";", 1)[0].strip().lower()
                if not content or mime not in IMAGE_EXTENSIONS:
                    raise ValueError("Not a supported image response")
                # Match crawl_lastest_news: URL extension first, then Content-Type.
                extension = Path(urlsplit(source_url).path).suffix.lower().lstrip(".")
                if not extension or not extension.isalnum() or len(extension) > 6:
                    extension = IMAGE_EXTENSIONS[mime]
                file_name = generate_image_path(row["article_id"], row["sequence_number"], extension)
                image_path = self._put_object(f"{folder}/{file_name}", content, mime, deadline)
                row["image_path"] = image_path
                row["status"] = "downloaded"
            except CrawlError as exc:
                if exc.code == "CRAWL_TIMEOUT":
                    raise
                row["status"] = "failed"
            except (requests.RequestException, MinioException, urllib3.exceptions.HTTPError, OSError, ValueError):
                deadline.remaining()
                row["status"] = "failed"
            if row["status"] == "failed":
                warnings.append({"code": "IMAGE_DOWNLOAD_FAILED", "sequence_number": row["sequence_number"], "message": "Could not download or upload the image; the source URL was kept in image_path."})

    def close(self):
        pass
