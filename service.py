from __future__ import annotations

import os
import time
import uuid
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .article_crawler import ArticleCrawler, SkipArticle, _normalize_internal_url
from .errors import CrawlError
from .http_client import HttpClient
from .repository import ArticleRepository
from .runtime import Deadline, DomainLimiter
from .schemas import CrawlRequest
from .serializers import build_article_export, build_export_from_rows
from .settings import Settings
from .site_resolver import resolve_site


class CrawlService:
    def __init__(self, settings: Settings, limiter: DomainLimiter, *, repository=None, client_factory=HttpClient):
        self.settings, self.limiter, self.client_factory = settings, limiter, client_factory
        self.repository = repository if repository is not None else ArticleRepository(settings)

    def _stored_export(self, data, request_id, status):
        return build_export_from_rows(
            data["articles"][0], data["article_images"], data["article_videos"],
            request_id=request_id, duration_ms=0, record_timezone=self.settings.record_timezone,
            source="db" if status == "existing" else "live", persistence_status=status,
        )

    def crawl(self, request: CrawlRequest, request_id: str, deadline: Deadline):
        started = time.monotonic()
        site = resolve_site(request.url)
        url = _normalize_internal_url(site.base_url, request.url, keep_query=site.keep_query_params)
        if not url:
            raise CrawlError("INVALID_URL", "The URL does not match this source.")
        if request.save_to_db:
            existing = self.repository.find(url, deadline)
            if existing:
                result = self._stored_export(existing, request_id, "existing")
                if request.download_images:
                    result["warnings"].append({"code": "EXISTING_MEDIA_UNCHANGED", "message": "This article already exists; its media has not been downloaded again."})
                result["duration_ms"] = int((time.monotonic() - started) * 1000)
                return result

        client = self.client_factory(site, self.settings, deadline, self.limiter)
        downloaded_paths: list[Path] = []
        persisted_images = False
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
                self._download_images(result, client, site, request_id, deadline, warnings, downloaded_paths)
            if request.save_to_db:
                deadline.remaining()
                data, status = self.repository.save(result["data"], deadline)
                persisted_images = status == "created"
                result = self._stored_export(data, request_id, status)
                if status == "existing":
                    warnings = [{"code": "ARTICLE_ALREADY_EXISTS", "message": "A concurrent request saved this URL; returning its stored data."}]
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
            if not persisted_images:
                self._cleanup_images(downloaded_paths)

    @staticmethod
    def _cleanup_images(paths: list[Path]) -> None:
        for path in paths:
            with suppress(OSError):
                path.unlink(missing_ok=True)
        if paths:
            for folder in (paths[0].parent, paths[0].parent.parent, paths[0].parent.parent.parent):
                with suppress(OSError):
                    folder.rmdir()

    def _download_images(self, export, client, site, request_id, deadline, warnings, downloaded_paths):
        now = datetime.now(ZoneInfo(self.settings.record_timezone))
        article_id = uuid.UUID(export["data"]["articles"][0]["id"])
        # Each request owns its files, including when another process wins the DB insert.
        folder = Path(self.settings.images_folder) / f"{now.day}_{now.month}_{now.year}" / str(article_id) / uuid.UUID(request_id).hex
        extensions = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif", "image/svg+xml": "svg", "image/bmp": "bmp", "image/tiff": "tiff"}
        for row in export["data"]["article_images"]:
            deadline.remaining()
            temporary = None
            try:
                content, content_type = client.get_bytes(row["image_path"], headers={"Referer": site.base_url})
                mime = (content_type or "").split(";", 1)[0].strip().lower()
                if not content or mime not in extensions:
                    raise ValueError("Not a supported image response")
                deadline.remaining()
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / f"{article_id}_img_{row['sequence_number']}.{extensions[mime]}"
                temporary = target.with_suffix(target.suffix + ".tmp")
                with temporary.open("xb") as output:
                    output.write(content)
                deadline.remaining()
                os.replace(temporary, target)
                downloaded_paths.append(target)
                row["image_path"], row["status"] = str(target.resolve()), "downloaded"
            except CrawlError as exc:
                if exc.code == "CRAWL_TIMEOUT":
                    raise
                row["status"] = "failed"
            except (requests.RequestException, OSError, ValueError):
                row["status"] = "failed"
            finally:
                if temporary is not None:
                    with suppress(OSError):
                        temporary.unlink(missing_ok=True)
            if row["status"] == "failed":
                warnings.append({"code": "IMAGE_DOWNLOAD_FAILED", "sequence_number": row["sequence_number"], "message": "The source URL was retained for a later retry."})

    def close(self):
        self.repository.close()
