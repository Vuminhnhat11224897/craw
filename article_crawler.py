from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Dict, List, Optional, Sequence, Set
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

from .config import SiteConfig
from .errors import CrawlError
from .settings import Settings
from .extractor.article import ArticleExtractor, _is_in_excluded_section, _prettify_slug, _render_moha_article_html, _render_mof_article_html

LOGGER = logging.getLogger(__name__)
_MOF_ROOT_SLUG = "bo-tai-chinh"
_MOHA_ID_RE = re.compile(r"---id(?P<id>\d+)", re.IGNORECASE)
_MIN_VIETNAMESE_LETTERS = 200
_MIN_VIETNAMESE_DIACRITICS = 3

@dataclass(slots=True)
class ParsedArticle:
    """Kết quả bóc tách 1 bài báo từ HTML."""

    url: str
    title: str
    description: Optional[str]
    content: Optional[str]
    category_id: Optional[str]
    category_name: Optional[str]
    tags: Sequence[str]
    publish_date: Optional[datetime]
    images: Sequence[str]
    videos: Sequence[str]

@dataclass(slots=True)
class CategoryInfo:
    url: str
    slug: str
    name: Optional[str] = None

class SkipArticle(Exception):
    """Raised when a crawled article should be ignored."""

def _normalize_internal_url(
    base_url: str,
    href: str,
    *,
    keep_query: bool = False,
) -> Optional[str]:
    """Chuẩn hoá link nội bộ: join với base_url, bỏ query/fragment, chỉ giữ đúng host."""
    href = (href or "").strip()
    if not href or href.lower().startswith(("javascript:", "mailto:", "tel:")):
        return None

    candidate = urljoin(base_url, href)
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return None

    base = urlparse(base_url)
    base_host = (base.hostname or "").lower()
    host = (parsed.hostname or "").lower()
    if not base_host or not host:
        return None

    root_host = base_host[4:] if base_host.startswith("www.") else base_host
    allowed_hosts = {
        base_host,
        root_host,
        f"www.{root_host}",
    }
    if host not in allowed_hosts and not host.endswith(f".{root_host}"):
        return None

    cleaned = parsed._replace(fragment="")
    if cleaned.port is not None:
        is_default_https = cleaned.scheme == "https" and cleaned.port == 443
        is_default_http = cleaned.scheme == "http" and cleaned.port == 80
        if is_default_https or is_default_http:
            cleaned = cleaned._replace(netloc=cleaned.hostname or cleaned.netloc)
    if not keep_query:
        cleaned = cleaned._replace(query="")
    return urlunparse(cleaned)

def _text_or_none(node: Optional[Tag]) -> Optional[str]:
    if not node:
        return None
    text = node.get_text(" ", strip=True)
    return text or None

def _extract_main_content(soup: BeautifulSoup) -> str:
    """
    Heuristic chung để lấy nội dung bài:
    - ưu tiên các selector thường gặp ở VNExpress/Tuổi Trẻ,
    - fallback: <article>, sau đó toàn bộ <body>.
    """
    candidates = [
        "article.fck_detail",
        "article#main-detail-body",
        "article.article",
        "div#main_detail",
        "div#content",
        "div#content_detail",
        "div.content-detail",
        "div.article-content",
        "div.b-maincontent",
    ]
    for selector in candidates:
        node = soup.select_one(selector)
        if node:
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in node.find_all(["p", "div"])
                if p.get_text(strip=True)
            ]
            if paragraphs:
                return "\n".join(paragraphs)

    node = soup.find("article")
    if node:
        text = node.get_text("\n", strip=True)
        return text

    body = soup.body
    if body:
        text = body.get_text("\n", strip=True)
        return text
    return ""

def _count_latin_diacritics(text: str) -> int:
    if not text:
        return 0
    count = 0
    for ch in text:
        if ch.isalpha():
            decomposed = unicodedata.normalize("NFD", ch)
            if any(unicodedata.combining(c) for c in decomposed[1:]):
                count += 1
    return count

def _looks_vietnamese(text: str) -> bool:
    if not text:
        return True
    letter_count = sum(1 for ch in text if ch.isalpha())
    if letter_count < _MIN_VIETNAMESE_LETTERS:
        return True
    if "đ" in text or "Đ" in text:
        return True
    return _count_latin_diacritics(text) >= _MIN_VIETNAMESE_DIACRITICS

def _moha_html_has_content(html: str) -> bool:
    if not html:
        return False
    soup = BeautifulSoup(html, "html.parser")
    for selector in (
        "div.mh-detail-body",
        "div.mh-detail-content",
        "div.moha-article__content",
        "article.moha-article",
    ):
        node = soup.select_one(selector)
        if not node:
            continue
        text = node.get_text(" ", strip=True)
        if text and len(text) >= 50:
            return True
    return False

def _extract_publish_date(soup: BeautifulSoup) -> Optional[datetime]:
    """Cố gắng lấy ngày publish từ các thẻ meta chuẩn (ISO 8601)."""
    meta = (
        soup.find("meta", attrs={"itemprop": "datePublished"})
        or soup.find("meta", attrs={"property": "article:published_time"})
        or soup.find("meta", attrs={"name": "pubdate"})
    )
    if not meta:
        return None
    value = (meta.get("content") or "").strip()
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None

def _extract_tags(soup: BeautifulSoup) -> List[str]:
    """Heuristic chung để lấy tags."""
    containers = soup.select(
        "div.tags, div.list-tag, ul.list-tag, ul.tag, section.wrap-tag, "
        "div.box-keyword, div.tag, section.tags"
    )
    tags: List[str] = []
    seen: Set[str] = set()

    for container in containers:
        for anchor in container.find_all("a"):
            text = anchor.get_text(strip=True)
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            tags.append(text)

    if not tags:
        for anchor in soup.select("a[rel='tag']"):
            text = anchor.get_text(strip=True)
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            tags.append(text)

    if not tags:
        for meta_name in ("news_keywords", "keywords"):
            meta_tag = soup.find("meta", attrs={"name": meta_name})
            if not meta_tag or not meta_tag.get("content"):
                continue
            for token in meta_tag["content"].split(","):
                text = token.strip()
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                tags.append(text)
            if tags:
                break

    return tags

def _extract_images_and_videos(soup: BeautifulSoup, base_url: str) -> tuple[List[str], List[str]]:
    """Lấy các link ảnh/video trong nội dung chính."""
    images: List[str] = []
    videos: List[str] = []
    seen_img: Set[str] = set()
    seen_video: Set[str] = set()

    for selector in ("article", "#content", "#main_detail", ".article-content", ".b-maincontent"):
        container = soup.select_one(selector)
        if not container:
            continue

        for img in container.find_all("img"):
            if _is_in_excluded_section(img):
                continue
            candidate = (
                img.get("data-src")
                or img.get("data-original")
                or img.get("data-lazy-src")
                or img.get("src")
            )
            url = _normalize_internal_url(base_url, candidate) if candidate else None
            if url and url not in seen_img:
                seen_img.add(url)
                images.append(url)

        for tag_name in ("video", "iframe", "source"):
            for node in container.find_all(tag_name):
                if _is_in_excluded_section(node):
                    continue
                candidate = node.get("src") or node.get("data-src")
                url = _normalize_internal_url(base_url, candidate) if candidate else None
                if url and url not in seen_video:
                    seen_video.add(url)
                    videos.append(url)

        if images or videos:
            break

    return images, videos

_NOT_FOUND_PAGE_NAMES = {"404", "not-found", "notfound", "page-not-found", "khong-tim-thay", "error-404", "loi-404"}


def _is_not_found_url(url: str) -> bool:
    segment = (urlparse(url).path or "/").rstrip("/").rsplit("/", 1)[-1].lower()
    return segment.rsplit(".", 1)[0] in _NOT_FOUND_PAGE_NAMES if segment else False


class ArticleCrawler:
    """Single-URL crawler with service-owned parsing rules and no persistence."""

    def __init__(self, site: SiteConfig, *, client, settings: Settings | None = None) -> None:
        self.site = site
        self.client = client
        self.settings = settings if settings is not None else Settings()

    def _normalize_url(self, href: str) -> Optional[str]:
        return _normalize_internal_url(
            self.site.base_url,
            href,
            keep_query=self.site.keep_query_params,
        )

    def fetch_article(self, url: str) -> ParsedArticle:
        """Fetch and parse a single article URL without discovering a category or using the DB."""
        normalized_url = self._normalize_url(url)
        if not normalized_url:
            raise SkipArticle(f"Article URL is not an internal site URL: {url}")
        if not self._is_allowed_article_host(normalized_url):
            raise SkipArticle(f"URL host is not allowed for site {self.site.key}: {url}")
        if not self._has_allowed_article_suffix(normalized_url) or not self._has_allowed_article_path(normalized_url):
            raise SkipArticle(f"URL does not match an article path for site {self.site.key}: {url}")
        if self._is_denied_article_url(normalized_url):
            raise SkipArticle(f"Article URL is excluded for site {self.site.key}: {url}")
        if self._is_home_url(normalized_url):
            raise SkipArticle(f"URL is the site home page: {url}")

        html = self._fetch_article_html(normalized_url)
        # Some sites redirect a missing article to the home page or a 404 page served
        # with status 200 (vnexpress: 302 -> /404.html) instead of returning 404.
        final_url = getattr(self.client, "last_url", None)
        if isinstance(final_url, str) and final_url != normalized_url and (
            self._is_home_url(final_url) or _is_not_found_url(final_url)
        ):
            raise CrawlError("ARTICLE_NOT_FOUND", "The article was not found on the news source.", 404)
        html = self._maybe_fetch_moha_article_html(normalized_url, html)
        html = self._maybe_fetch_mof_article_html(normalized_url, html)
        parsed = self._parse_article(
            html,
            url=normalized_url,
            category=None,
            allow_missing_category=True,
        )
        if not parsed.content:
            raise SkipArticle(f"Missing article content for {normalized_url}")
        return parsed

    def _fetch_article_html(self, url: str) -> str:
        try:
            return self.client.get(url)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if self.site.key == "moh" and (status_code is None or status_code >= 500):
                for fallback_url in self._moh_article_url_fallbacks(url):
                    try:
                        html = self.client.get(fallback_url)
                    except requests.RequestException:
                        continue
                    LOGGER.info(
                        "Fetched MOH article via fallback URL %s (original %s)",
                        fallback_url,
                        url,
                    )
                    return html
            raise
        except requests.RequestException:
            if self.site.key != "moh":
                raise
            for fallback_url in self._moh_article_url_fallbacks(url):
                try:
                    html = self.client.get(fallback_url)
                except requests.RequestException:
                    continue
                LOGGER.info(
                    "Fetched MOH article via fallback URL %s (original %s)",
                    fallback_url,
                    url,
                )
                return html
            raise

    def _moh_article_url_fallbacks(self, url: str) -> List[str]:
        parsed = urlparse(url)
        path = parsed.path or "/"
        variants: List[str] = []

        def add_path(candidate_path: str) -> None:
            if not candidate_path.startswith("/"):
                candidate_path = f"/{candidate_path}"
            candidate_url = urlunparse(parsed._replace(path=candidate_path))
            if candidate_url != url and candidate_url not in variants:
                variants.append(candidate_url)

        def strip_locale_segment(candidate_path: str) -> str | None:
            segments = [seg for seg in candidate_path.split("/") if seg]
            if not segments:
                return None
            locales = {"vi_vn", "vi-vn", "vi"}
            first = segments[0].lower()
            if first in locales:
                return "/" + "/".join(segments[1:]) if len(segments) > 1 else "/"
            if (
                len(segments) >= 3
                and segments[0] == "web"
                and segments[1] == "guest"
                and segments[2].lower() in locales
            ):
                remainder = segments[:2] + segments[3:]
                return "/" + "/".join(remainder) if remainder else "/"
            return None

        stripped = strip_locale_segment(path)
        if stripped is not None:
            add_path(stripped)

        if not path.startswith("/web/guest/") and path != "/web/guest":
            guest_path = "/web/guest" + (path if path.startswith("/") else f"/{path}")
            add_path(guest_path)
            stripped_guest = strip_locale_segment(guest_path)
            if stripped_guest is not None:
                add_path(stripped_guest)

        return variants

    def _maybe_fetch_moha_article_html(self, url: str, html: str) -> str:
        if self.site.key != "moha":
            return html
        if not self._should_use_moha_api(url, html):
            return html
        article_id = self._extract_moha_id(url)
        if not article_id:
            return html
        try:
            payload = self.client.get_json(
                f"{self.settings.moha_api_base.rstrip('/')}/PostDetail",
                params={"ID": article_id},
            )
        except requests.RequestException as exc:
            LOGGER.warning("Failed to fetch moha article %s: %s", url, exc)
            return html
        api_html = _render_moha_article_html(payload)
        if api_html and _moha_html_has_content(api_html):
            return api_html
        return html

    def _maybe_fetch_mof_article_html(self, url: str, html: str) -> str:
        if self.site.key != "mof":
            return html
        if not self._should_use_mof_api(url, html):
            return html
        slug = self._extract_mof_slug(url)
        if not slug:
            return html
        try:
            payload = self.client.get_json(
                f"{self.settings.mof_api_base.rstrip('/')}/article/getbyslug",
                params={"slug": slug},
            )
        except requests.RequestException as exc:
            LOGGER.warning("Failed to fetch mof article %s: %s", url, exc)
            return html
        api_html = _render_mof_article_html(payload)
        return api_html or html

    def _should_use_moha_api(self, url: str, html: str) -> bool:
        if not self._extract_moha_id(url):
            return False
        parsed = urlparse(url)
        domain = (parsed.hostname or parsed.netloc).lower()
        if not (domain == "moha.gov.vn" or domain.endswith(".moha.gov.vn")):
            return False
        if '<div id="root"></div>' in html:
            return True
        return not _moha_html_has_content(html)

    def _should_use_mof_api(self, url: str, html: str) -> bool:
        if not self._extract_mof_slug(url):
            return False
        parsed = urlparse(url)
        domain = (parsed.hostname or parsed.netloc).lower()
        if not (domain == "mof.gov.vn" or domain.endswith(".mof.gov.vn")):
            return False
        if '<div id="app"></div>' in html or '<div id="app">' in html:
            return True
        return "<title>" in html and "</title>" in html and "<div id=\"app\"" in html

    @staticmethod
    def _extract_moha_id(url: str) -> str | None:
        match = _MOHA_ID_RE.search(url or "")
        if not match:
            return None
        return match.group("id")

    @staticmethod
    def _extract_mof_slug(url: str) -> str | None:
        path = urlparse(url).path or ""
        parts = [segment for segment in path.split("/") if segment]
        if not parts:
            return None
        slug = parts[-1].strip()
        if slug in {"mof", "btc", _MOF_ROOT_SLUG, "search", "content"}:
            return None
        return slug or None

    def _is_home_url(self, url: str) -> bool:
        path = (urlparse(url).path or "/").rstrip("/")
        home_path = (getattr(self.site, "home_path", None) or "/").rstrip("/")
        return path in ("", home_path) or path.lower() in ("/index.html", "/index.htm", "/index.php", "/home")

    def _is_denied_article_url(self, url: str) -> bool:
        prefixes = getattr(self.site, "deny_article_prefixes", ())
        if not prefixes:
            return False
        parsed = urlparse(url)
        path = parsed.path or "/"
        for prefix in prefixes:
            if not prefix:
                continue
            normalized_prefix = prefix if prefix.startswith("/") else f"/{prefix}"
            if path.startswith(normalized_prefix):
                return True
        return False

    def _is_allowed_article_host(self, url: str) -> bool:
        suffixes = getattr(self.site, "allowed_article_host_suffixes", ())
        deny_prefixes = getattr(self.site, "deny_article_host_prefixes", ())
        if not suffixes:
            suffixes = ()
        normalized_suffixes = [
            suffix.strip().lower().lstrip(".")
            for suffix in suffixes
            if suffix and suffix.strip()
        ]
        parsed = urlparse(url)
        host = (parsed.hostname or parsed.netloc).lower()
        if host.startswith("www."):
            host = host[4:]
        if deny_prefixes:
            normalized_denies = [
                prefix.strip().lower()
                for prefix in deny_prefixes
                if prefix and prefix.strip()
            ]
            if any(host.startswith(prefix) for prefix in normalized_denies):
                return False
        if not normalized_suffixes:
            return True
        return any(host == suffix or host.endswith(f".{suffix}") for suffix in normalized_suffixes)

    def _has_allowed_article_suffix(self, url: str) -> bool:
        suffixes = getattr(self.site, "allowed_article_url_suffixes", ())
        if not suffixes:
            return True
        normalized_suffixes = [
            suffix.strip().lower()
            for suffix in suffixes
            if suffix and suffix.strip()
        ]
        if not normalized_suffixes:
            return True
        return any(url.lower().endswith(suffix) for suffix in normalized_suffixes)

    def _has_allowed_article_path(self, url: str) -> bool:
        patterns = getattr(self.site, "allowed_article_path_regexes", ())
        if not patterns:
            return True
        path = urlparse(url).path or "/"
        for pattern in patterns:
            if not pattern:
                continue
            try:
                if re.search(pattern, path):
                    return True
            except re.error:
                LOGGER.warning("Invalid allowed_article_path_regex: %s", pattern)
        return False

    def _parse_article(
        self,
        html: str,
        *,
        url: str,
        category: CategoryInfo | None,
        allow_missing_category: bool = False,
    ) -> ParsedArticle:
        soup = BeautifulSoup(html, "html.parser")

        skip_locale, locale_value = self._should_skip_locale(soup)
        if skip_locale and self.site.key != "laodong":
            raise SkipArticle(
                f"Unsupported locale '{locale_value}' for article {url}",
            )

        extractor = ArticleExtractor(url)
        data = extractor.extract(html)

        forced_category_id = getattr(self.site, "forced_category_id", None)
        forced_category_name = getattr(self.site, "forced_category_name", None)
        if forced_category_id:
            data.category_id = forced_category_id
        if forced_category_name:
            data.category_name = forced_category_name

        title = data.title or url
        placeholder_title = f"{self.site.base_url.rstrip('/')}/404"
        if title and title.strip().lower() == placeholder_title.lower():
            raise SkipArticle(f"Placeholder 404 page for article {url}")

        description = data.description or data.summary
        if not description:
            desc_node: Optional[Tag] = None
            if getattr(self.site, "description_selectors", None):
                for selector in self.site.description_selectors:
                    node = soup.select_one(selector)
                    if node:
                        desc_node = node
                        break
            if desc_node is None:
                desc_node = (
                    soup.select_one("p.description")
                    or soup.select_one("p.sapo")
                    or soup.select_one("h2.sapo")
                    or soup.select_one("h2.detail-sapo")
                )
            description = _text_or_none(desc_node)

        content = data.content or _extract_main_content(soup) or None
        if content and len(content.strip()) < 50:
            raise SkipArticle(f"Missing article content for {url}")
        if not content or not content.strip():
            content = None

        if self.site.key == "laodong":
            combined_text = " ".join(part for part in (title, description, content) if part)
            if skip_locale and not _looks_vietnamese(combined_text):
                raise SkipArticle(
                    f"Unsupported locale '{locale_value}' for article {url}",
                )
            if not _looks_vietnamese(combined_text):
                raise SkipArticle(f"Non-Vietnamese content for article {url}")

        # Nếu bản thân trang bài không có category_id và category_name
        # (do ArticleExtractor không trích được từ HTML) thì bỏ qua.
        # Những URL này thường là trang thể loại/bộ sưu tập, không phải bài báo cụ thể.
        if not (data.category_id or data.category_name):
            # Riêng với một số site, ta fallback dùng slug category từ trang danh sách.
            # - vov: trang bài thường không có meta category rõ ràng.
            # - vnexpress: ArticleExtractor chưa trích được category, nhưng slug từ trang
            #   danh sách đã phản ánh đúng chuyên mục (thoi-su, kinh-doanh, ...).
            if category and self.site.key in (
                "vov",
                "vnexpress",
                "baocaobang",
                "baovinhlong",
                "baodienbienphu",
                "thanhtra",
                "modgov",
            ):
                data.category_id = category.slug
                data.category_name = category.name or _prettify_slug(category.slug)
            elif not allow_missing_category:
                raise SkipArticle(
                    f"Missing category id and name for article {url}",
                )

        category_id = data.category_id or (category.slug if category else None)
        category_name = data.category_name
        if not category_name:
            breadcrumb = soup.select_one("ul.breadcrumb, nav.breadcrumb")
            if breadcrumb:
                tokens: List[str] = []
                for li in breadcrumb.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        tokens.append(text)
                if tokens:
                    category_name = tokens[-1]

        if forced_category_id:
            category_id = forced_category_id
        if forced_category_name:
            category_name = forced_category_name

        if self.site.key == "vietbao" and not allow_missing_category:
            normalized_category_id = (category_id or "").strip().lower()
            has_category_name = bool((category_name or "").strip())
            if not has_category_name or normalized_category_id in ("", "root"):
                raise SkipArticle(f"Missing category for vietbao article {url}")

        publish_date = data.publish_date or _extract_publish_date(soup) or datetime.now(timezone.utc)

        if data.tags:
            tags_list: List[str] = [
                part.strip() for part in data.tags.split(",") if part.strip()
            ]
        else:
            tags_list = _extract_tags(soup)

        blocked_images = set(self.settings.blocked_image_urls)
        images = [image for image in data.images if image not in blocked_images]
        videos = list(data.videos)
        if not images and not videos:
            images, videos = _extract_images_and_videos(soup, base_url=self.site.base_url)
        images = [image for image in images if image not in blocked_images]

        return ParsedArticle(
            url=url,
            title=title,
            description=description,
            content=content,
            category_id=category_id,
            category_name=category_name,
            tags=tags_list,
            publish_date=publish_date,
            images=images,
            videos=videos,
        )

    def _should_skip_locale(self, soup: BeautifulSoup) -> tuple[bool, Optional[str]]:
        allowed = getattr(self.site, "allowed_locales", ())
        if not allowed:
            return False, None

        normalized_allowed = tuple(
            token.strip().lower().replace("_", "-")
            for token in allowed
            if token and token.strip()
        )
        if not normalized_allowed:
            return False, None

        locales = []
        html_tag = soup.find("html")
        if html_tag:
            for attr in ("lang", "xml:lang"):
                value = html_tag.get(attr)
                if value:
                    locales.append(value)
                    break

        for attrs in (
            {"property": "og:locale"},
            {"property": "article:language"},
            {"name": "language"},
            {"name": "dc.language"},
            {"http-equiv": "content-language"},
        ):
            meta = soup.find("meta", attrs=attrs)
            if meta and meta.get("content"):
                locales.append(meta["content"])

        normalized_locales = [
            token.strip().lower().replace("_", "-")
            for token in locales
            if token and token.strip()
        ]
        if not normalized_locales:
            return False, None

        for locale in normalized_locales:
            for allowed_locale in normalized_allowed:
                if locale.startswith(allowed_locale):
                    return False, None

        return True, normalized_locales[0]

    @staticmethod
    def _join_tags(tags: Sequence[str]) -> Optional[str]:
        cleaned: List[str] = []
        seen: Set[str] = set()
        for tag in tags:
            value = (tag or "").strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(value)
        if not cleaned:
            return None
        concatenated = ", ".join(cleaned)
        return concatenated[:500]

    @staticmethod
    def _trim_to_column_length(value: Optional[str], column_attr) -> Optional[str]:
        if value is None:
            return None
        column = column_attr.property.columns[0]
        max_length = getattr(column.type, "length", None)
        if not max_length or len(value) <= max_length:
            return value
        LOGGER.debug(
            "Truncating value for %s from %d to %d characters",
            column.key,
            len(value),
            max_length,
        )
        return value[:max_length]

