from __future__ import annotations

import os
import math
import uuid
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import dotenv_values, load_dotenv


_SAMPLE = dotenv_values(Path(__file__).with_name(".env.sample"))


def _default(name: str) -> str:
    value = _SAMPLE.get(name)
    if value is None:
        raise ValueError(f"Missing default in realtime .env.sample: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    article_namespace: str = ""
    record_timezone: str = _default("RECORD_TIMEZONE")
    max_concurrent_crawls: int = int(_default("MAX_CONCURRENT_CRAWLS"))
    max_queued_crawls: int = int(_default("MAX_QUEUED_CRAWLS"))
    queue_timeout: float = float(_default("QUEUE_TIMEOUT_SECONDS"))
    crawl_timeout: float = float(_default("CRAWL_TIMEOUT_SECONDS"))
    connect_timeout: float = float(_default("CONNECT_TIMEOUT_SECONDS"))
    read_timeout: float = float(_default("READ_TIMEOUT_SECONDS"))
    max_retries: int = int(_default("HTTP_MAX_RETRIES"))
    max_html_bytes: int = int(_default("MAX_HTML_BYTES"))
    max_image_bytes: int = int(_default("MAX_IMAGE_BYTES"))
    max_videos_per_article: int = int(_default("MAX_VIDEOS_PER_ARTICLE"))
    images_folder: str = _default("IMAGES_FOLDER")
    videos_folder: str = _default("VIDEOS_FOLDER")
    blocked_image_urls: tuple[str, ...] = tuple(value.strip() for value in _default("BLOCKED_IMAGE_URLS").split(",") if value.strip())
    http_user_agent: str = _default("HTTP_USER_AGENT")
    http_accept: str = _default("HTTP_ACCEPT")
    http_json_accept: str = _default("HTTP_JSON_ACCEPT")
    http_image_accept: str = _default("HTTP_IMAGE_ACCEPT")
    http_accept_language: str = _default("HTTP_ACCEPT_LANGUAGE")
    default_domain_delay: float = float(_default("DEFAULT_DOMAIN_DELAY_SECONDS"))
    max_redirects: int = int(_default("HTTP_MAX_REDIRECTS"))
    http_chunk_bytes: int = int(_default("HTTP_CHUNK_BYTES"))
    retry_backoff_cap: float = float(_default("RETRY_BACKOFF_CAP_SECONDS"))
    retry_after_seconds: int = int(_default("RETRY_AFTER_SECONDS"))
    moha_api_base: str = _default("MOHA_API_BASE")
    mof_api_base: str = _default("MOF_API_BASE")

    @classmethod
    def from_env(cls) -> "Settings":
        # Load only this service's file, never search parent or sibling projects.
        load_dotenv(Path(__file__).with_name(".env"), override=False)
        return cls(
            api_key=os.getenv("INTERNAL_API_KEY", ""),
            article_namespace=os.getenv("ARTICLE_UUIDV5_NAMESPACE", ""),
            record_timezone=os.getenv("RECORD_TIMEZONE", cls.record_timezone),
            max_concurrent_crawls=int(os.getenv("MAX_CONCURRENT_CRAWLS", str(cls.max_concurrent_crawls))),
            max_queued_crawls=int(os.getenv("MAX_QUEUED_CRAWLS", str(cls.max_queued_crawls))),
            queue_timeout=float(os.getenv("QUEUE_TIMEOUT_SECONDS", str(cls.queue_timeout))),
            crawl_timeout=float(os.getenv("CRAWL_TIMEOUT_SECONDS", str(cls.crawl_timeout))),
            connect_timeout=float(os.getenv("CONNECT_TIMEOUT_SECONDS", str(cls.connect_timeout))),
            read_timeout=float(os.getenv("READ_TIMEOUT_SECONDS", str(cls.read_timeout))),
            max_retries=int(os.getenv("HTTP_MAX_RETRIES", str(cls.max_retries))),
            max_html_bytes=int(os.getenv("MAX_HTML_BYTES", str(cls.max_html_bytes))),
            max_image_bytes=int(os.getenv("MAX_IMAGE_BYTES", str(cls.max_image_bytes))),
            max_videos_per_article=int(os.getenv("MAX_VIDEOS_PER_ARTICLE", str(cls.max_videos_per_article))),
            images_folder=os.getenv("IMAGES_FOLDER", cls.images_folder),
            videos_folder=os.getenv("VIDEOS_FOLDER", cls.videos_folder),
            blocked_image_urls=tuple(value.strip() for value in os.getenv("BLOCKED_IMAGE_URLS", ",".join(cls.blocked_image_urls)).split(",") if value.strip()),
            http_user_agent=os.getenv("HTTP_USER_AGENT", cls.http_user_agent),
            http_accept=os.getenv("HTTP_ACCEPT", cls.http_accept),
            http_json_accept=os.getenv("HTTP_JSON_ACCEPT", cls.http_json_accept),
            http_image_accept=os.getenv("HTTP_IMAGE_ACCEPT", cls.http_image_accept),
            http_accept_language=os.getenv("HTTP_ACCEPT_LANGUAGE", cls.http_accept_language),
            default_domain_delay=float(os.getenv("DEFAULT_DOMAIN_DELAY_SECONDS", str(cls.default_domain_delay))),
            max_redirects=int(os.getenv("HTTP_MAX_REDIRECTS", str(cls.max_redirects))),
            http_chunk_bytes=int(os.getenv("HTTP_CHUNK_BYTES", str(cls.http_chunk_bytes))),
            retry_backoff_cap=float(os.getenv("RETRY_BACKOFF_CAP_SECONDS", str(cls.retry_backoff_cap))),
            retry_after_seconds=int(os.getenv("RETRY_AFTER_SECONDS", str(cls.retry_after_seconds))),
            moha_api_base=os.getenv("MOHA_API_BASE", cls.moha_api_base),
            mof_api_base=os.getenv("MOF_API_BASE", cls.mof_api_base),
        )

    def validate(self) -> None:
        if not self.api_key.strip():
            raise ValueError("INTERNAL_API_KEY is required")
        uuid.UUID(self.article_namespace)
        ZoneInfo(self.record_timezone)
        if self.max_queued_crawls < 0 or not math.isfinite(self.queue_timeout) or self.queue_timeout <= 0:
            raise ValueError("MAX_QUEUED_CRAWLS cannot be negative and QUEUE_TIMEOUT_SECONDS must be positive")
        if not all(math.isfinite(value) for value in (self.crawl_timeout, self.connect_timeout, self.read_timeout, self.default_domain_delay, self.retry_backoff_cap)):
            raise ValueError("Timeouts must be finite")
        if min(self.max_concurrent_crawls, self.crawl_timeout, self.connect_timeout, self.read_timeout, self.max_html_bytes, self.max_image_bytes, self.max_videos_per_article) <= 0 or self.max_retries < 0:
            raise ValueError("Timeouts, limits and concurrency must be positive; retries cannot be negative")
        if self.default_domain_delay < 0 or self.retry_backoff_cap < 0 or self.max_redirects < 0 or self.http_chunk_bytes < 1 or self.retry_after_seconds < 1:
            raise ValueError("HTTP limits and retry values must be valid")
        if not all(value.strip() for value in (self.images_folder, self.videos_folder, self.http_user_agent, self.http_accept, self.http_json_accept, self.http_image_accept, self.http_accept_language)):
            raise ValueError("HTTP headers and media folders must not be empty")
        from urllib.parse import urlsplit
        for name, value in (("MOHA_API_BASE", self.moha_api_base), ("MOF_API_BASE", self.mof_api_base)):
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError(f"{name} must be an HTTPS base URL")
