"""Download queued article images and update each DB row after its MinIO upload."""

from __future__ import annotations

import logging
import os
import signal
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text

from .http_client import HttpClient
from .image_jobs import image_object_key
from .runtime import Deadline, DomainLimiter
from .service import IMAGE_EXTENSIONS, put_object
from .settings import Settings
from .site_resolver import resolve_site

LOGGER = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
LEASE_SECONDS = 120
RETRY_SECONDS = (30, 120, 600, 1800)


def claim(engine):
    token = uuid.uuid4()
    with engine.begin() as connection:
        row = connection.execute(text("""
            WITH selected AS (
                SELECT image_id FROM image_download_jobs
                WHERE attempts < :max_attempts
                  AND ((status = 'pending' AND next_attempt_at <= now())
                       OR (status = 'processing' AND locked_until < now()))
                ORDER BY next_attempt_at, image_id
                FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE image_download_jobs AS jobs
            SET status = 'processing', attempts = jobs.attempts + 1,
                claim_token = :token,
                locked_until = now() + :lease * interval '1 second'
            FROM selected
            LEFT JOIN article_images AS images ON images.id = selected.image_id
            WHERE jobs.image_id = selected.image_id
            RETURNING jobs.image_id, jobs.source_url, jobs.article_url,
                      jobs.object_key, jobs.attempts, jobs.claim_token, jobs.created_at,
                      images.article_id, images.sequence_number
        """), {"token": token, "lease": LEASE_SECONDS, "max_attempts": MAX_ATTEMPTS}).mappings().first()
    return dict(row) if row else None


def finish(engine, job, image_url):
    with engine.begin() as connection:
        owned = connection.execute(text("""
            SELECT image_id FROM image_download_jobs
            WHERE image_id = :image_id AND claim_token = :claim_token
              AND status = 'processing' FOR UPDATE
        """), job).first()
        if not owned:
            return False
        updated = connection.execute(text("""
            UPDATE article_images SET image_path = :image_url, status = 'downloaded'
            WHERE id = :image_id AND status IN ('pending', 'failed')
              AND image_path = :source_url
        """), {**job, "image_url": image_url}).rowcount
        connection.execute(text("""
            UPDATE image_download_jobs
            SET status = :status, locked_until = NULL, claim_token = NULL,
                last_error = :last_error, object_key = :object_key
            WHERE image_id = :image_id AND claim_token = :claim_token
        """), {**job, "status": "downloaded" if updated else "failed",
               "last_error": None if updated else "Image row changed or removed during download"})
        if not updated:
            LOGGER.warning("image_id=%s image row changed or removed; job marked failed", job["image_id"])
        return bool(updated)


def fail(engine, job, error, *, terminal=False):
    terminal = terminal or job["attempts"] >= MAX_ATTEMPTS
    with engine.begin() as connection:
        updated = connection.execute(text("""
            UPDATE image_download_jobs
            SET status = :status, next_attempt_at = now() + :delay * interval '1 second',
                locked_until = NULL, claim_token = NULL, last_error = :error
            WHERE image_id = :image_id AND claim_token = :claim_token
              AND status = 'processing'
        """), {**job, "status": "failed" if terminal else "pending",
                "delay": 0 if terminal else RETRY_SECONDS[job["attempts"] - 1],
                "error": str(error)[:1000]}).rowcount
        if terminal and updated:
            connection.execute(text("""
                UPDATE article_images SET status = 'failed'
                WHERE id = :image_id AND status = 'pending' AND image_path = :source_url
            """), job)


def expire_exhausted(engine):
    with engine.begin() as connection:
        connection.execute(text("""
            WITH exhausted AS (
                UPDATE image_download_jobs SET status = 'failed',
                    locked_until = NULL, claim_token = NULL,
                    last_error = 'Worker stopped during final attempt'
                WHERE status = 'processing' AND attempts >= :max_attempts
                    AND locked_until < now()
                RETURNING image_id, source_url
            )
            UPDATE article_images AS images SET status = 'failed'
            FROM exhausted WHERE images.id = exhausted.image_id
                AND images.status = 'pending' AND images.image_path = exhausted.source_url
        """), {"max_attempts": MAX_ATTEMPTS})


def process(engine, job, settings, limiter):
    deadline = Deadline(60)
    client = None
    try:
        site = resolve_site(job["article_url"])
        client = HttpClient(site, settings, deadline, limiter)
        content, content_type = client.get_bytes(job["source_url"], headers={"Referer": site.base_url})
        mime = (content_type or "").split(";", 1)[0].strip().lower()
        if not content or mime not in IMAGE_EXTENSIONS:
            raise ValueError("Unsupported or empty image response")
        if job["object_key"].startswith("articles/"):
            if job["article_id"] is None or job["sequence_number"] is None:
                raise ValueError("Image row was removed before download")
            day = job["created_at"].astimezone(ZoneInfo(settings.record_timezone))
            job["object_key"] = image_object_key(job["article_id"], job["sequence_number"], day)
        job["object_key"] = str(PurePosixPath(job["object_key"]).with_suffix("." + IMAGE_EXTENSIONS[mime]))
        image_url = put_object(settings, job["object_key"], content, mime, deadline)
        if finish(engine, job, image_url):
            LOGGER.info("image_id=%s status=downloaded bytes=%d", job["image_id"], len(content))
    except Exception as exc:
        terminal = isinstance(exc, ValueError) or getattr(exc, "code", None) == "INVALID_URL"
        # requests responses expose status_code; MinIO S3Error wraps a urllib3 response with status.
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None) or getattr(response, "status", None)
        if status:
            terminal = terminal or (400 <= status < 500 and status != 429)
        LOGGER.warning("image_id=%s attempt=%s error=%s", job["image_id"], job["attempts"], exc)
        fail(engine, job, exc, terminal=terminal)
    finally:
        if client:
            client.close()


def run_worker(engine, settings, limiter, stop):
    while not stop.is_set():
        try:
            expire_exhausted(engine)
            job = claim(engine)
            if job:
                process(engine, job, settings, limiter)
            else:
                stop.wait(2)
        except Exception:
            LOGGER.exception("Image worker error")
            stop.wait(5)


def main():
    settings = Settings.from_env()
    settings.validate()
    if not all((settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key)):
        raise ValueError("MINIO_ENDPOINT, MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required")
    database_url = os.environ["ARTICLE_DATABASE_URL"]
    workers = int(os.getenv("IMAGE_WORKERS", "4"))
    if not 1 <= workers <= 16:
        raise ValueError("IMAGE_WORKERS must be between 1 and 16")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    engine = create_engine(database_url, pool_pre_ping=True, pool_size=workers, max_overflow=0)
    limiter = DomainLimiter()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_worker, engine, settings, limiter, stop) for _ in range(workers)]
            stop.wait()
            for future in futures:
                future.result()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
