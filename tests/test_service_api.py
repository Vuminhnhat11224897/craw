import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import uuid
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager
from urllib3.response import HTTPResponse

from craw_real_times.app import create_app
from craw_real_times.errors import CrawlError
from craw_real_times.runtime import Deadline, DomainLimiter
from craw_real_times.schemas import CrawlRequest
from craw_real_times.service import CrawlService
from craw_real_times.settings import Settings


HTML = '''<html lang="vi"><head><meta property="og:title" content="Bài báo thử nghiệm"></head>
<body><article><p>Nội dung bài báo được viết bằng tiếng Việt với đầy đủ thông tin để nhận diện.</p>
<p>Đây là đoạn tiếp theo của bài viết, dùng để kiểm tra kết quả xuất dữ liệu.</p></article></body></html>'''


class ServiceApiTests(unittest.TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings = Settings(api_key="test-key", article_namespace=str(uuid.NAMESPACE_URL),
                                 minio_endpoint="http://minio.example:9000", minio_access_key="test-user",
                                 minio_secret_key="test-password")
        storage_patch = patch("craw_real_times.service.Minio")
        self.storage_factory = storage_patch.start()
        self.addCleanup(storage_patch.stop)
        self.storage = self.storage_factory.return_value
        self.objects = {}

        def put_object(bucket, key, data, length, **kwargs):
            content = data.read()
            self.assertEqual(len(content), length)
            self.assertEqual(bucket, "news-article-images")
            self.objects[key] = content

        self.storage.put_object.side_effect = put_object
        clock_patch = patch("craw_real_times.service.datetime")
        clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        clock.now.return_value = datetime(2026, 9, 28, 9, 0, tzinfo=ZoneInfo(self.settings.record_timezone))
        self.client = Mock()
        self.client.get.return_value = HTML
        self.service = CrawlService(self.settings, DomainLimiter(), client_factory=lambda *args: self.client)

    def test_default_mode_writes_no_media(self):
        result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/story.html"), "request-test", Deadline(5))
        self.assertEqual(result["data"]["articles"][0]["title"], "Bài báo thử nghiệm")
        self.assertNotIn("media", result)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])
        self.storage_factory.assert_not_called()

    def test_download_uploads_images_without_saving_any_metadata(self):
        self.client.get.return_value = HTML.replace("</article>", '<img src="/a.jpg"><img src="/b.png"><video src="/clip.mp4"></video></article>')
        self.client.get_bytes.side_effect = [(b"jpg-bytes", "image/jpeg"), (b"<html>", "text/html")]
        with patch.object(Path, "write_text", side_effect=AssertionError("No local metadata")), patch.object(Path, "write_bytes", side_effect=AssertionError("No local media")):
            result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/bai-viet-thu-123.html", download_images=True), "request-test", Deadline(5))

        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://vnexpress.net/bai-viet-thu-123.html"))
        self.assertEqual(result["data"]["articles"][0]["id"], article_id)
        folder = f"{self.settings.minio_endpoint}/news-article-images/28_9_2026"
        key = f"28_9_2026/{article_id}_img_1.jpg"
        self.assertEqual(result["media"]["images_folder"], folder)
        self.assertEqual(self.objects[key], b"jpg-bytes")
        self.assertEqual(list(self.objects), [key])
        self.assertEqual(self.storage.put_object.call_count, 1)
        images = result["data"]["article_images"]
        self.assertEqual((images[0]["status"], images[0]["image_path"]), ("downloaded", f"{folder}/{article_id}_img_1.jpg"))
        self.assertEqual((images[1]["status"], images[1]["image_path"]), ("failed", "https://vnexpress.net/b.png"))
        self.assertIsNone(result["media"]["images_metadata"])
        self.assertIsNone(result["media"]["videos_metadata"])
        self.assertEqual(self.storage_factory.call_args.args, ("minio.example:9000",))
        self.assertFalse(self.storage_factory.call_args.kwargs["secure"])
        self.assertEqual(self.storage_factory.call_args.kwargs["access_key"], "test-user")
        self.assertEqual(list(Path(self.media.name).iterdir()), [])
        self.assertEqual(result["data"]["article_videos"][0]["video_path"], "https://vnexpress.net/clip.mp4")
        self.assertIn("IMAGE_DOWNLOAD_FAILED", [w["code"] for w in result["warnings"]])

    def test_recrawl_reuses_daily_key_and_matches_latest_extension_rule(self):
        self.client.get.return_value = HTML.replace("</article>", '<img src="/a.jpg"></article>')
        self.client.get_bytes.return_value = (b"one", "image/png")
        request = CrawlRequest(url="https://vnexpress.net/bai.html", download_images=True)
        first = self.service.crawl(request, "first", Deadline(5))
        self.client.get_bytes.return_value = (b"two", "image/jpeg")
        second = self.service.crawl(request, "second", Deadline(5))
        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://vnexpress.net/bai.html"))
        self.assertEqual(first["data"]["article_images"][0]["image_path"], second["data"]["article_images"][0]["image_path"])
        self.assertEqual(self.objects[f"28_9_2026/{article_id}_img_1.jpg"], b"two")
        self.assertEqual(len(self.objects), 1)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])

    def test_upload_failure_keeps_original_image_and_video_urls(self):
        self.client.get.return_value = HTML.replace("</article>", '<img src="/a.jpg"><video src="/clip.mp4"></video></article>')
        self.client.get_bytes.return_value = (b"jpg-bytes", "image/jpeg")
        self.storage.put_object.side_effect = S3Error("AccessDenied", "Denied", "", "", "", None)
        result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/bai.html", download_images=True), "request-test", Deadline(5))
        image = result["data"]["article_images"][0]
        self.assertEqual((image["status"], image["image_path"]), ("failed", "https://vnexpress.net/a.jpg"))
        self.assertIsNone(result["media"]["images_metadata"])
        self.assertIsNone(result["media"]["videos_metadata"])
        self.assertEqual(result["data"]["article_videos"][0]["video_path"], "https://vnexpress.net/clip.mp4")
        self.assertIn("IMAGE_DOWNLOAD_FAILED", [w["code"] for w in result["warnings"]])
        self.assertEqual(self.storage.put_object.call_count, 1)

    def test_real_sdk_sends_signed_put_with_unchanged_image_bytes(self):
        self.storage_factory.side_effect = Minio
        key = "28_9_2026/article_img_1.jpg"
        with patch.object(PoolManager, "urlopen", return_value=HTTPResponse(status=200, headers={"ETag": '"test-etag"'})) as upload:
            path = self.service._put_object(key, b"original-image", "image/jpeg", Deadline(5))
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(upload.call_args.args, ("PUT", f"http://minio.example:9000/news-article-images/{key}"))
        self.assertEqual(upload.call_args.kwargs["body"], b"original-image")
        self.assertEqual(upload.call_args.kwargs["headers"]["Content-Type"], "image/jpeg")
        self.assertTrue(upload.call_args.kwargs["headers"]["Authorization"].startswith("AWS4-HMAC-SHA256 "))
        self.assertEqual(path, upload.call_args.args[1])

    def test_deadline_stops_uploads(self):
        self.client.get.return_value = HTML.replace("</article>", '<img src="/a.jpg"></article>')
        deadline = Deadline(5)

        def download(*args, **kwargs):
            deadline.cancelled.set()
            return b"jpg-bytes", "image/jpeg"

        self.client.get_bytes.side_effect = download
        with self.assertRaises(CrawlError) as error:
            self.service.crawl(CrawlRequest(url="https://vnexpress.net/bai.html", download_images=True), "request-test", deadline)
        self.assertEqual(error.exception.code, "CRAWL_TIMEOUT")
        self.storage_factory.assert_not_called()

    def test_missing_minio_config_only_blocks_download_mode(self):
        self.service.settings = replace(self.settings, minio_endpoint="", minio_access_key="", minio_secret_key="")
        result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/story.html"), "request-test", Deadline(5))
        self.assertEqual(result["status"], "success")
        with self.assertRaises(CrawlError) as error:
            self.service.crawl(CrawlRequest(url="https://vnexpress.net/story.html", download_images=True), "request-test", Deadline(5))
        self.assertEqual(error.exception.code, "MEDIA_STORAGE_NOT_CONFIGURED")
        with self.assertRaises(ValueError):
            replace(self.settings, minio_endpoint="http://100.91.202.88:9001/browser/news-article-images").validate()

    def test_api_returns_utf8_attachment_and_requires_key(self):
        with TestClient(create_app(self.settings, service=self.service)) as client:
            denied = client.post("/internal/v1/articles/crawl", json={"url": "https://vnexpress.net/story.html"})
            self.assertEqual(denied.status_code, 401)
            result = client.post("/internal/v1/articles/crawl", headers={"X-API-Key": "test-key"}, json={"url": "https://vnexpress.net/story.html"})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertTrue(result.headers["content-disposition"].startswith('attachment; filename="article_'))
            self.assertEqual(result.headers["content-type"], "application/json")
            self.assertEqual(json.loads(result.content)["data"]["articles"][0]["title"], "Bài báo thử nghiệm")
            self.assertEqual(client.get("/health/ready").status_code, 200)
            self.assertEqual(client.get("/internal/openapi.json").status_code, 401)

    def test_removed_save_to_db_option_is_rejected(self):
        with TestClient(create_app(self.settings, service=self.service)) as client:
            response = client.post("/internal/v1/articles/crawl", headers={"X-API-Key": "test-key"}, json={"url": "https://vnexpress.net/story.html", "save_to_db": True})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("content-disposition", response.headers)
