"""Write image jobs in the same transaction as their image rows."""

from sqlalchemy import text


def enqueue_images(session, article_url: str, images) -> None:
    rows = [
        {
            "image_id": image["id"],
            "source_url": image["image_path"],
            "article_url": article_url,
            "object_key": f"articles/{image['article_id']}/{image['id']}",
        }
        for image in images if image["image_path"]
    ]
    if rows:
        session.execute(text("""
            INSERT INTO image_download_jobs (image_id, source_url, article_url, object_key)
            VALUES (:image_id, :source_url, :article_url, :object_key)
            ON CONFLICT (image_id) DO UPDATE SET
                source_url = EXCLUDED.source_url,
                article_url = EXCLUDED.article_url,
                object_key = EXCLUDED.object_key,
                status = 'pending', attempts = 0, next_attempt_at = now(),
                locked_until = NULL, claim_token = NULL, last_error = NULL
            WHERE image_download_jobs.status = 'failed'
        """), rows)
