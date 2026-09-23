import unittest
from unittest.mock import Mock, patch

import requests

from craw_real_times.config.base import SiteConfig
from craw_real_times.errors import CrawlError
from craw_real_times.http_client import HttpClient
from craw_real_times.runtime import Deadline, DomainLimiter
from craw_real_times.settings import Settings


def response(status=200, body=b"ok", headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = body
    result._content_consumed = True
    result.headers.update(headers or {})
    result.url = "https://example.com/article.html"
    return result


class HttpClientTests(unittest.TestCase):
    def make_client(self, **settings):
        client = HttpClient(SiteConfig(key="example", base_url="https://example.com", delay_seconds=0), Settings(**settings), Deadline(3), DomainLimiter())
        self.addCleanup(client.close)
        return client

    def test_checks_redirect_destination_before_sending_another_request(self):
        client = self.make_client()
        client.session.request = Mock(return_value=response(302, headers={"Location": "http://127.0.0.1/private"}))
        def validate(url):
            if "127.0.0.1" in url:
                raise CrawlError("INVALID_URL", "Private destination")
        with patch("craw_real_times.http_client.validate_public_url", side_effect=validate):
            with self.assertRaises(CrawlError):
                client.get("https://example.com/article.html")
        self.assertEqual(client.session.request.call_count, 1)

    def test_limits_body_size_even_without_content_length(self):
        client = self.make_client(max_html_bytes=3)
        client.session.request = Mock(return_value=response(body=b"1234"))
        with patch("craw_real_times.http_client.validate_public_url"):
            with self.assertRaises(CrawlError) as caught:
                client.get("https://example.com/article.html")
        self.assertEqual(caught.exception.code, "UPSTREAM_ERROR")

    def test_decodes_utf8_vietnamese_without_assuming_latin1(self):
        client = self.make_client()
        client.session.request = Mock(return_value=response(body="Tiếng Việt".encode("utf-8")))
        with patch("craw_real_times.http_client.validate_public_url"):
            self.assertEqual(client.get("https://example.com/article.html"), "Tiếng Việt")
