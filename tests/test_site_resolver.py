import socket
import unittest
from unittest.mock import patch

from craw_real_times.errors import CrawlError
from craw_real_times.site_resolver import resolve_site, validate_public_url


class SiteResolverTests(unittest.TestCase):
    def test_exact_host_and_duplicate_configuration_are_deterministic(self):
        self.assertEqual(resolve_site("https://www.vnexpress.net/story.html").key, "vnexpress")
        self.assertEqual(resolve_site("https://vtv.gov.vn/news/story").key, "vtvgov")
        self.assertEqual(resolve_site("https://dongkhoi.baovinhlong.vn/story-a123.html").key, "baodongkhoi")

    def test_rejects_unknown_and_deceptive_hosts(self):
        for url in ("https://vnexpress.net.evil.vn/a", "https://unknown.vn/a", "file:///etc/passwd", "https://user:pass@vnexpress.net/a", "http://vnexpress.net:8080/a"):
            with self.subTest(url=url), self.assertRaises(CrawlError):
                resolve_site(url)

    def test_rejects_private_dns_answers_and_mixed_answers(self):
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch("craw_real_times.site_resolver.socket.getaddrinfo", return_value=answers):
            with self.assertRaises(CrawlError):
                validate_public_url("https://vnexpress.net/a")


if __name__ == "__main__":
    unittest.main()
