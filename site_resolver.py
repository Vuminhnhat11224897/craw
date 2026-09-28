from __future__ import annotations

import ipaddress
import socket
from functools import lru_cache
from urllib.parse import urlsplit

from .config import get_supported_sites
from .config.base import SiteConfig
from .errors import CrawlError


def parse_url(url: str):
    try:
        parsed = urlsplit(url)
        if (
            not url or len(url) > 2000 or any(ord(char) < 32 for char in url)
            or "\\" in url or parsed.scheme not in ("http", "https")
            or not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 80 if parsed.scheme == "http" else 443)
        ):
            raise ValueError("Invalid URL")
        parsed.hostname.encode("idna")
        return parsed
    except (ValueError, UnicodeError):
        raise CrawlError("INVALID_URL", "URL must be an HTTP(S) article URL without credentials or a custom port.") from None


def _host(value: str) -> str:
    return value.lower().rstrip(".").removeprefix("www.")


@lru_cache(maxsize=1)
def supported_sites() -> dict[str, SiteConfig]:
    return get_supported_sites()


def resolve_site(url: str) -> SiteConfig:
    host = _host(parse_url(url).hostname or "")
    sites = supported_sites()
    exact = [cfg for cfg in sites.values() if _host(urlsplit(cfg.base_url).hostname or "") == host]
    if exact:
        # Both reference configurations target the same publisher. Keep one stable identity.
        if host == "dongkhoi.baovinhlong.vn":
            return sites["baodongkhoi"]
        return exact[0]
    candidates: list[tuple[int, SiteConfig]] = []
    for cfg in sites.values():
        roots = [urlsplit(cfg.base_url).hostname or "", *cfg.allowed_article_host_suffixes]
        for value in roots:
            root = _host(value.lstrip("."))
            if len(root.split(".")) >= 2 and (host == root or host.endswith("." + root)):
                candidates.append((len(root), cfg))
    if candidates:
        candidates.sort(key=lambda item: (-item[0], item[1].key))
        return candidates[0][1]
    raise CrawlError("UNSUPPORTED_SITE", "This news source is not configured.")


def validate_public_url(url: str) -> None:
    parsed = parse_url(url)
    try:
        answers = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise CrawlError("UPSTREAM_ERROR", "Could not resolve the upstream host.", 502, retryable=True) from None
    if not answers:
        raise CrawlError("UPSTREAM_ERROR", "Upstream DNS returned no addresses.", 502, retryable=True)
    for answer in answers:
        address = ipaddress.ip_address(answer[4][0].split("%", 1)[0])
        if not address.is_global or address.is_multicast:
            raise CrawlError("INVALID_URL", "Fetching private or reserved network addresses is not allowed.")
