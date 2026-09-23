import json
import unittest
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
        self.settings = Settings(api_key="test-key", article_namespace=str(uuid.NAMESPACE_URL))
        self.repository = Mock()
        self.client = Mock()
        self.client.get.return_value = HTML
        self.service = CrawlService(self.settings, DomainLimiter(), repository=self.repository, client_factory=lambda *args: self.client)

    def test_default_mode_never_accesses_repository(self):
        result = self.service.crawl(CrawlRequest(url="https://vnexpress.net/story.html"), "request-test", Deadline(5))
        self.assertEqual(result["persistence_status"], "not_requested")
        self.assertEqual(result["data"]["articles"][0]["title"], "Bài báo thử nghiệm")
        self.repository.find.assert_not_called()
        self.repository.save.assert_not_called()

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

    def test_download_requires_explicit_save_flag(self):
        with TestClient(create_app(self.settings, service=self.service)) as client:
            response = client.post("/internal/v1/articles/crawl", headers={"X-API-Key": "test-key"}, json={"url": "https://vnexpress.net/story.html", "download_images": True})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("content-disposition", response.headers)
