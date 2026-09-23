from __future__ import annotations

import re
import ssl
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter

from .config.base import SiteConfig
from .errors import CrawlError
from .runtime import Deadline, DomainLimiter
from .settings import Settings
from .site_resolver import validate_public_url


class _SSLAdapter(HTTPAdapter):
    def __init__(self, context):
        self.context = context
        super().__init__()

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.context
        return super().init_poolmanager(*args, **kwargs)


class HttpClient:
    """Bounded, deadline-aware fetching for article HTML, fallback APIs and images."""

    def __init__(self, site: SiteConfig, settings: Settings, deadline: Deadline, limiter: DomainLimiter):
        self.site, self.settings, self.deadline, self.limiter = site, settings, deadline, limiter
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": settings.http_user_agent,
            "Accept": settings.http_accept,
            "Accept-Language": settings.http_accept_language,
            **site.request_headers,
        })
        if site.allow_legacy_ssl or site.allow_weak_dh_ssl:
            context = ssl.create_default_context()
            if site.allow_legacy_ssl:
                context.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
            if site.allow_weak_dh_ssl:
                context.set_ciphers("DEFAULT@SECLEVEL=1")
            if site.allow_insecure_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            root = (urlsplit(site.base_url).hostname or "").removeprefix("www.")
            adapter = _SSLAdapter(context)
            for host in (root, "www." + root):
                self.session.mount("https://" + host + "/", adapter)

    def close(self):
        self.session.close()

    @staticmethod
    def _text(response: requests.Response) -> str:
        try:
            return response.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return response.content.decode(response.apparent_encoding or "utf-8", errors="replace")

    def get(self, url, *, params=None, headers=None):
        return self._text(self._request(url, params=params, headers=headers, max_bytes=self.settings.max_html_bytes))

    def get_json(self, url, *, params=None, headers=None):
        response = self._request(url, params=params, headers={"Accept": self.settings.http_json_accept, **(headers or {})}, max_bytes=self.settings.max_html_bytes)
        try:
            return response.json()
        except ValueError:
            raise CrawlError("UPSTREAM_ERROR", "The upstream API returned invalid JSON.", 502) from None

    def get_bytes(self, url, *, params=None, headers=None):
        response = self._request(url, params=params, headers={"Accept": self.settings.http_image_accept, **(headers or {})}, max_bytes=self.settings.max_image_bytes)
        return response.content, response.headers.get("Content-Type")

    def _request(self, url, *, params, headers, max_bytes):
        retries = min(self.settings.max_retries, max(self.site.max_retries, 0))
        for attempt in range(retries + 1):
            self.deadline.remaining()
            try:
                result = self._follow_redirects(url, params=params, headers=headers, max_bytes=max_bytes)
                text = self._text(result) if "image" not in (result.headers.get("Content-Type") or "").lower() else ""
                match = re.search(r'document\.cookie\s*=\s*"D1N=([^";]+)', text)
                if match:
                    self.session.cookies.set("D1N", match.group(1), domain=urlsplit(result.url).hostname, path="/")
                    raise requests.HTTPError("Upstream cookie challenge", response=result)
                if any(marker.lower() in text.lower() for marker in self.site.blocked_content_markers if marker):
                    raise requests.HTTPError("Upstream blocked response", response=result)
                return result
            except requests.RequestException as exc:
                response = exc.response
                status = response.status_code if response is not None else None
                if attempt >= retries or (status is not None and status not in (200, 429, 500, 502, 503, 504)):
                    raise
                retry_after = response.headers.get("Retry-After", "") if response is not None else ""
                backoff = min(max(self.site.retry_backoff, 0) * (2 ** attempt), self.settings.retry_backoff_cap)
                wait = max(float(retry_after) if retry_after.isdigit() else 0, backoff)
                self.deadline.wait(wait)
        raise CrawlError("UPSTREAM_ERROR", "Could not fetch the upstream page.", 502)

    def _follow_redirects(self, url, *, params, headers, max_bytes):
        current = url
        for _ in range(self.settings.max_redirects + 1):
            self.deadline.remaining()
            validate_public_url(current)
            host = urlsplit(current).hostname or ""
            delay = max(self.site.delay_seconds if self.site.delay_seconds is not None else self.settings.default_domain_delay, 0)
            with self.limiter.request(host, delay, self.deadline):
                remaining = self.deadline.remaining()
                with self.session.request(
                    "GET", current, params=params, headers=headers,
                    timeout=(min(self.settings.connect_timeout, remaining), min(self.settings.read_timeout, remaining)),
                    allow_redirects=False, stream=True,
                    verify=not (self.site.allow_insecure_ssl and host.removeprefix("www.") == (urlsplit(self.site.base_url).hostname or "").removeprefix("www.")),
                ) as response:
                    self.deadline.remaining()
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            raise CrawlError("UPSTREAM_ERROR", "The upstream redirect has no destination.", 502)
                        current = urljoin(current, location)
                        params = None
                        continue
                    response.raise_for_status()
                    length = response.headers.get("Content-Length", "")
                    if length.isdigit() and int(length) > max_bytes:
                        raise CrawlError("UPSTREAM_ERROR", "The upstream response exceeds the size limit.", 502)
                    body = bytearray()
                    for chunk in response.iter_content(chunk_size=self.settings.http_chunk_bytes):
                        self.deadline.remaining()
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise CrawlError("UPSTREAM_ERROR", "The upstream response exceeds the size limit.", 502)
                    response._content = bytes(body)
                    response._content_consumed = True
                    return response
        raise CrawlError("UPSTREAM_ERROR", "Too many upstream redirects.", 502)
