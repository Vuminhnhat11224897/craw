from __future__ import annotations

import time
import uuid
from io import BytesIO
from urllib.parse import urlsplit

import requests
import urllib3
from minio import Minio

from .article_crawler import ArticleCrawler, SkipArticle, _normalize_internal_url
from .errors import CrawlError
from .http_client import HttpClient
from .runtime import Deadline, DomainLimiter
from .schemas import CrawlRequest
from .serializers import build_article_export
from .settings import Settings
from .site_resolver import resolve_site

IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif", "image/svg+xml": "svg", "image/bmp": "bmp", "image/tiff": "tiff"}


def put_object(settings, key, content, content_type, deadline):
    remaining = deadline.remaining()
    endpoint = urlsplit(settings.minio_endpoint)
    with urllib3.PoolManager(
        timeout=urllib3.Timeout(total=remaining, connect=remaining, read=remaining), retries=False,
    ) as http:
        storage = Minio(endpoint.netloc, secure=endpoint.scheme == "https",
                        access_key=settings.minio_access_key, secret_key=settings.minio_secret_key,
                        region=settings.minio_region, http_client=http)
        storage.put_object(settings.minio_bucket, key, BytesIO(content), len(content),
                           content_type=content_type, part_size=max(len(content), 5 * 1024 * 1024))
    deadline.remaining()
    return f"/{settings.minio_bucket}/{key}"


class CrawlService:
    def __init__(self, settings: Settings, limiter: DomainLimiter, *, client_factory=HttpClient):
        self.settings, self.limiter, self.client_factory = settings, limiter, client_factory

    def crawl(self, request: CrawlRequest, request_id: str, deadline: Deadline):
        started = time.monotonic()
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

    def close(self):
        pass
