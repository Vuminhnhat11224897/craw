from __future__ import annotations

import json
import os
import shutil
import threading
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
from .runtime import Deadline, DomainLimiter
from .schemas import CrawlRequest
from .serializers import build_article_export
from .settings import Settings
from .site_resolver import resolve_site

IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif", "image/svg+xml": "svg", "image/bmp": "bmp", "image/tiff": "tiff"}
METADATA_FILE = "metadata.json"
# Swapping a staged folder into place must not interleave for the same article.
_PUBLISH_LOCK = threading.Lock()


def _write_json(path: Path, payload) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


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
            if request.download_images:
                result["media"] = self._save_media(result, client, site, request_id, deadline, warnings)
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

    def _media_header(self, export, request_id):
        article = export["data"]["articles"][0]
        return {
            "article_id": article["id"], "url": article["url"], "title": article["title"],
            "article_name": article["article_name"], "publish_date": article["publish_date"],
            "crawled_at": datetime.now(ZoneInfo(self.settings.record_timezone)).isoformat(),
            "request_id": request_id,
        }

    def _save_media(self, export, client, site, request_id, deadline, warnings):
        article = export["data"]["articles"][0]
        # One folder per article, named by its URL-derived UUIDv5 so re-crawls reuse it.
        name = article["id"]
        header = self._media_header(export, request_id)
        media = {"images_folder": None, "images_metadata": None, "videos_metadata": None}
        try:
            if export["data"]["article_images"]:
                images_root = Path(self.settings.images_folder).resolve()
                target = images_root / name
                images = self._download_images(export, client, site, deadline, warnings, images_root, target)
                # Write metadata after the swap so it always describes the files on disk.
                _write_json(target / METADATA_FILE, {**header, "images": images})
                media["images_folder"], media["images_metadata"] = str(target), str(target / METADATA_FILE)
            if export["data"]["article_videos"]:
                videos_root = Path(self.settings.videos_folder).resolve()
                target = videos_root / name
                target.mkdir(parents=True, exist_ok=True)
                videos = [{"sequence_number": row["sequence_number"], "video_url": row["video_path"]} for row in export["data"]["article_videos"]]
                _write_json(target / METADATA_FILE, {**header, "videos": videos})
                media["videos_metadata"] = str(target / METADATA_FILE)
        except OSError:
            warnings.append({"code": "MEDIA_SAVE_FAILED", "message": "Could not write media files or metadata; source URLs are kept in the response."})
        return media

    def _download_images(self, export, client, site, deadline, warnings, root: Path, target: Path):
        # Download into a private staging folder, then swap it in so a failed or
        # concurrent re-crawl never leaves a half-written article folder.
        root.mkdir(parents=True, exist_ok=True)
        staging = root / f".{target.name}.{uuid.uuid4().hex}.tmp"
        staging.mkdir()
        images = []
        try:
            for row in export["data"]["article_images"]:
                deadline.remaining()
                source_url, entry = row["image_path"], {"sequence_number": row["sequence_number"], "source_url": row["image_path"]}
                try:
                    content, content_type = client.get_bytes(source_url, headers={"Referer": site.base_url})
                    mime = (content_type or "").split(";", 1)[0].strip().lower()
                    if not content or mime not in IMAGE_EXTENSIONS:
                        raise ValueError("Not a supported image response")
                    deadline.remaining()
                    file_name = f"img_{row['sequence_number']}.{IMAGE_EXTENSIONS[mime]}"
                    (staging / file_name).write_bytes(content)
                    entry.update(file_name=file_name, local_path=str(target / file_name), content_type=mime, size_bytes=len(content), status="downloaded")
                except CrawlError as exc:
                    if exc.code == "CRAWL_TIMEOUT":
                        raise
                    entry["status"] = "failed"
                except (requests.RequestException, OSError, ValueError):
                    entry["status"] = "failed"
                if entry["status"] == "failed":
                    warnings.append({"code": "IMAGE_DOWNLOAD_FAILED", "sequence_number": row["sequence_number"], "message": "The source URL was kept in image_path."})
                images.append(entry)
            deadline.remaining()
            with _PUBLISH_LOCK:
                previous = root / f".{target.name}.{uuid.uuid4().hex}.old"
                if target.exists():
                    os.rename(target, previous)
                os.rename(staging, target)
            shutil.rmtree(previous, ignore_errors=True)
            for row, entry in zip(export["data"]["article_images"], images):
                row["status"] = entry["status"]
                if entry["status"] == "downloaded":
                    row["image_path"] = entry["local_path"]
            return images
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def close(self):
        pass
