import json
import tempfile
import unittest
from pathlib import Path
import uuid
from unittest.mock import Mock

from fastapi.testclient import TestClient

from craw_real_times.app import create_app
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
        root = Path(self.media.name)
        self.settings = Settings(api_key="test-key", article_namespace=str(uuid.NAMESPACE_URL),
                                 images_folder=str(root / "images"), videos_folder=str(root / "videos"))
        self.client = Mock()
        self.client.get.return_value = HTML
        self.service = CrawlService(self.settings, DomainLimiter(), client_factory=lambda *args: self.client)

    def test_default_mode_writes_no_media(self):
        result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/story.html"), "request-test", Deadline(5))
        self.assertEqual(result["data"]["articles"][0]["title"], "Bài báo thử nghiệm")
        self.assertNotIn("media", result)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])

    def test_download_saves_images_and_video_metadata_in_article_id_folders(self):
        self.client.get.return_value = HTML.replace("</article>", '<img src="/a.jpg"><img src="/b.png"><video src="/clip.mp4"></video></article>')
        self.client.get_bytes.side_effect = [(b"jpg-bytes", "image/jpeg"), (b"<html>", "text/html")]
        result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/bai-viet-thu-123.html", download_images=True), "request-test", Deadline(5))

        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://vnexpress.net/bai-viet-thu-123.html"))
        self.assertEqual(result["data"]["articles"][0]["id"], article_id)
        folder = Path(self.settings.images_folder).resolve() / article_id
        self.assertEqual(result["media"]["images_folder"], str(folder))
        self.assertEqual((folder / "img_1.jpg").read_bytes(), b"jpg-bytes")
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["img_1.jpg", "metadata.json"])
        images = result["data"]["article_images"]
        self.assertEqual((images[0]["status"], images[0]["image_path"]), ("downloaded", str(folder / "img_1.jpg")))
        self.assertEqual((images[1]["status"], images[1]["image_path"]), ("failed", "https://vnexpress.net/b.png"))
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["article_id"], result["data"]["articles"][0]["id"])
        self.assertEqual([i["status"] for i in metadata["images"]], ["downloaded", "failed"])

        video_folder = Path(self.settings.videos_folder).resolve() / article_id
        self.assertEqual(sorted(p.name for p in video_folder.iterdir()), ["metadata.json"])
        videos = json.loads((video_folder / "metadata.json").read_text(encoding="utf-8"))["videos"]
        self.assertEqual(videos, [{"sequence_number": 1, "video_url": "https://vnexpress.net/clip.mp4"}])
        self.assertIn("IMAGE_DOWNLOAD_FAILED", [w["code"] for w in result["warnings"]])

    def test_recrawl_replaces_folder_without_leftovers(self):
        self.client.get.return_value = HTML.replace("</article>", '<img src="/a.jpg"></article>')
        self.client.get_bytes.return_value = (b"one", "image/png")
        request = CrawlRequest(url="https://vnexpress.net/bai.html", download_images=True)
        self.service.crawl(request, "first", Deadline(5))
        self.client.get_bytes.return_value = (b"two", "image/jpeg")
        self.service.crawl(request, "second", Deadline(5))
        root = Path(self.settings.images_folder)
        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://vnexpress.net/bai.html"))
        self.assertEqual(sorted(p.name for p in root.iterdir()), [article_id])
        self.assertEqual(sorted(p.name for p in (root / article_id).iterdir()), ["img_1.jpg", "metadata.json"])

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
