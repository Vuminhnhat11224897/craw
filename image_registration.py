"""Persist requested image rows and jobs before accepting the request."""

import uuid

from sqlalchemy import text

from .image_jobs import enqueue_images


def save_crawl_images(engine, export):
    article = export["data"]["articles"][0]
    images = export["data"]["article_images"]
    if not images:
        return
    article_id = uuid.UUID(article["id"])
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS text), 0))"), {"id": article_id})
        existing = {row.sequence_number: row for row in connection.execute(text("""
            SELECT id, sequence_number, image_path, status FROM article_images
            WHERE article_id = :article_id ORDER BY created_at, id
        """), {"article_id": article_id})}
        to_insert = []
        to_queue = []
        for image in images:
            old = existing.get(image["sequence_number"])
            if old:
                image["id"] = str(old.id)
                if old.status == "downloaded":
                    image["image_path"], image["status"] = old.image_path, "downloaded"
                    continue
                if old.status in (None, "pending") and old.image_path.startswith(("http://", "https://")):
                    image["image_path"], image["status"] = old.image_path, "pending"
                    if old.status is None:
                        connection.execute(text("UPDATE article_images SET status = 'pending' WHERE id = :id"), {"id": old.id})
                elif old.status == "failed":
                    connection.execute(text("""
                        UPDATE article_images SET image_path = :path, status = 'pending' WHERE id = :id
                    """), {"id": old.id, "path": image["image_path"]})
                    image["status"] = "pending"
                else:
                    image["image_path"], image["status"] = old.image_path, old.status
                    continue
            else:
                to_insert.append(image)
            to_queue.append(image)
        if to_insert:
            connection.execute(text("""
                INSERT INTO article_images (id, article_id, image_path, status, sequence_number, created_at)
                VALUES (:id, :article_id, :image_path, 'pending', :sequence_number, now())
            """), to_insert)
        enqueue_images(connection, article["url"], to_queue)
