import hashlib
import json
import logging
import posixpath
import re
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape, unescape
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, FeatureNotFound, NavigableString, Tag
from dateutil import parser as date_parser

from .site_config import ArticleSiteConfig, get_article_site_config
from .utils import parse_w3c_datetime


logger = logging.getLogger(__name__)

_PG_UNIQUE_VIOLATION = "23505"
_ARTICLE_DEDUPE_CONSTRAINT_NAMES = (
    "articles_url_key",
    "articles_pkey",
)



_MOHA_ARTICLE_ID_RE = re.compile(r"---id(?P<id>\d+)", re.IGNORECASE)
_BAOQUANGNGAI_OUTPUTDATA_RE = re.compile(
    r'outputData\s*=\s*"(?P<html>(?:\\.|[^"\\])*)"',
    re.DOTALL,
)
_BAOQUANGNGAI_CONTENT_HTML_RE = re.compile(
    r"\\$\\('#content'\\)\\.html\\(`(?P<html>.*?)`\\);",
    re.DOTALL,
)

def _make_soup(markup: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(markup, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(markup, "html.parser")


@dataclass
class ArticleData:
    url: str
    title: str | None = None
    description: str | None = None
    summary: str | None = None
    content_html: str | None = None
    content: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    tags: str | None = None
    publish_date: datetime | None = None
    last_modified: datetime | None = None
    author: str | None = None
    external_id: str | None = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)


class ArticleExtractor:
    """Extract structured article information from HTML content."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc.lower()
        self.site_config: ArticleSiteConfig | None = get_article_site_config(self.domain)

    def extract(self, html: str) -> ArticleData:
        soup = _make_soup(html)
        self._inject_script_rendered_html(soup)
        data = ArticleData(url=self.base_url)
        data.title = self._extract_title(soup)
        data.description = self._extract_description(soup)
        data.summary = self._extract_summary(soup)
        # logger.info("Extracted description: %s", data.description)
        # logger.info("Extracted summary: %s", data.summary)

        main_container = self._find_main_container(soup)
        main_container = self._prune_main_container(main_container)

        extra_image_scopes: list[Tag] = []
        extra_image_scopes.extend(self._description_image_scopes(soup))
        extra_image_scopes.extend(self._summary_image_scopes(soup))

        data.content_html = self._extract_content_html(main_container)
        data.content = self._extract_content(soup, main_container)
        data.category_id, data.category_name = self._extract_category(soup)
        data.tags = self._extract_tags(soup)
        data.publish_date = self._extract_publish_date(soup)
        data.last_modified = self._extract_last_modified(soup)
        data.author = self._extract_author(soup)

        restrict_media_to_body = bool(self.site_config and self.site_config.inline_media_only)
        allow_extensionless_images = self._allow_extensionless_images()

        inline_images = self._extract_inline_images(
            soup,
            main_container,
            extra_scopes=extra_image_scopes,
        )
        metadata_images: list[str] = []
        if not restrict_media_to_body:
            metadata_images = self._extract_media_urls(
                soup,
                ["meta[property='og:image']", "meta[name='og:image']"],
                "content",
                skip_predicate=lambda url: self._should_skip_image_url(
                    url, allow_extensionless=allow_extensionless_images
                ),
            )

        # Prefer images that are part of the article body; only fall back to metadata
        # images when none were found to avoid storing redundant site-wide thumbnails.
        if inline_images and self.site_config and self.site_config.include_metadata_images:
            data.images = metadata_images + inline_images
        else:
            data.images = inline_images or metadata_images
        data.images = _deduplicate_preserve_order(data.images)

        data.videos = self._extract_media_urls(
            soup,
            ["meta[property='og:video']"],
            "content",
            skip_predicate=_should_skip_video_candidate,
        )
        data.videos.extend(self._extract_inline_videos(soup, main_container))
        data.videos = _deduplicate_preserve_order(data.videos)
        data.videos = _filter_domain_video_urls(self.domain, data.videos)

        return data

    def _inject_script_rendered_html(self, soup: BeautifulSoup) -> None:
        if not self.domain.endswith("baoquangngai.vn"):
            return
        content = soup.select_one("#content")
        if not content or content.get_text(strip=True):
            return
        html = _extract_baoquangngai_inline_html(soup)
        if not html:
            return
        fragment = _make_soup(html)
        payload = fragment.body or fragment
        for child in list(payload.contents):
            content.append(child)

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        if self.site_config and self.site_config.title_selectors:
            title = _first_text(soup, self.site_config.title_selectors)
            if title:
                return title

        selectors = [
            "meta[property='og:title']",
            "meta[name='og:title']",
            "meta[name='title']",
            "h1",
            "title",
        ]
        title = _first_text(soup, selectors)
        if title:
            return title

        # fallback to other heading levels if nothing found
        heading = soup.find(["h2", "h3"])
        if heading:
            text = heading.get_text(" ", strip=True)
            return _normalize_whitespace(text) or None
        return None

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        if self.site_config and self.site_config.description_selectors:
            description = _first_text(soup, self.site_config.description_selectors)
            if description:
                return _clean_description_text(description)
        selectors = [
            "meta[name='description']",
            "meta[property='og:description']",
            "p.summary",
            ".news-sapo p b",
        ]
        description = _first_text(soup, selectors)
        # logger.info("description %s", description)
        if description:
            return _clean_description_text(description)
        return None

    def _description_image_scopes(self, soup: BeautifulSoup) -> List[Tag]:
        if self.site_config and self.site_config.description_selectors:
            selectors = list(self.site_config.description_selectors)
        else:
            selectors = [
                "meta[name='description']",
                "meta[property='og:description']",
                "p.summary",
                ".news-sapo p b",
            ]
        return self._non_meta_scopes_for_selectors(soup, selectors)

    def _extract_summary(self, soup: BeautifulSoup) -> str | None:
        selectors = [
            "div.article__sapo",
            "div.article__lead",
            "div.article__desc",
            "div.cms-desc",
            "[itemprop='description']",
            ".article-sapo",
            ".article-summary",
            ".news-sapo p b"
        ]
        for selector in selectors:
            element = soup.select_one(selector)
            if not element:
                continue
            text = element.get_text(" ", strip=True)
            # print(text)
            text = _normalize_whitespace(text)
            if text:
                return text
        return None

    def _summary_image_scopes(self, soup: BeautifulSoup) -> List[Tag]:
        selectors = [
            "div.article__sapo",
            "div.article__lead",
            "div.article__desc",
            "div.cms-desc",
            "[itemprop='description']",
            ".article-sapo",
            ".article-summary",
            ".news-sapo p b",
        ]
        return self._non_meta_scopes_for_selectors(soup, selectors)

    def _non_meta_scopes_for_selectors(
        self,
        soup: BeautifulSoup,
        selectors: Sequence[str],
    ) -> List[Tag]:
        scopes: List[Tag] = []
        for selector in selectors:
            element = soup.select_one(selector)
            if not element or element.name == "meta":
                continue
            scopes.append(element)
            if isinstance(element.parent, Tag):
                scopes.append(element.parent)
            break
        return scopes

    def _extract_content_html(self, container: Tag | None) -> str | None:
        if container is None:
            return None
        soup_fragment = _make_soup(str(container))
        root = soup_fragment.find()
        if root is None:
            return None

        for selector in ["script", "style", "noscript", "iframe", "form"]:
            for element in root.select(selector):
                element.decompose()

        for selector in [
            ".rennab",
            ".adsbygoogle",
            ".adv-box",
            ".box-adv",
            "[data-position*='SdaArticle']",
        ]:
            for element in root.select(selector):
                element.decompose()

        for img in root.find_all("img"):
            data_src = img.get("data-src") or img.get("data-original")
            if data_src and not img.get("src"):
                img["src"] = data_src

        cleaned_html = root.decode_contents().strip()
        return cleaned_html or None

    def _extract_content(self, soup: BeautifulSoup, container: Tag | None = None) -> str | None:
        if container is None:
            container = self._find_main_container(soup)
        if container is None:
            paragraphs = [
                p
                for p in soup.find_all("p")
                if not _contains_excluded_text(p) and not _is_in_excluded_section(p)
            ]
            if paragraphs:
                return _join_paragraphs(paragraphs)
            return None

        if self.domain.endswith("moit.gov.vn"):
            paragraphs = [
                p
                for p in container.find_all("p")
                if not _contains_excluded_text(p) and not _is_in_excluded_section(p)
            ]
            if paragraphs:
                return _join_paragraphs(paragraphs)

        collected_texts: List[str] = []
        last_text: str | None = None
        queue: deque[Tag] = deque([container])
        blockish_tags = {
            "article",
            "aside",
            "blockquote",
            "div",
            "dl",
            "figure",
            "footer",
            "form",
            "header",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "main",
            "nav",
            "ol",
            "p",
            "pre",
            "section",
            "table",
            "ul",
        }

        while queue:
            current = queue.popleft()
            for child in current.children:
                if not isinstance(child, Tag):
                    continue
                if child.name in {"script", "style", "noscript", "iframe", "form"}:
                    continue
                if child.name in {"nav", "aside", "footer"}:
                    continue
                if _is_in_excluded_section(child):
                    continue

                if child.name in {"p", "h2", "h3", "h4", "li"}:
                    if child.name == "li" and self.domain.endswith("baocamau.vn"):
                        text_chunks: List[str] = []
                        for node in child.descendants:
                            if not isinstance(node, NavigableString):
                                continue
                            if node.find_parent("a"):
                                continue
                            raw = str(node).strip()
                            if raw:
                                text_chunks.append(raw)
                        text = " ".join(text_chunks)
                    else:
                        text = child.get_text(" ", strip=True)
                    text = _normalize_whitespace(text)
                    if not text:
                        continue
                    if _contains_excluded_text(text):
                        continue
                    if text == last_text:
                        continue
                    collected_texts.append(text)
                    last_text = text
                elif child.name == "table":
                    table_text = _table_to_text(child)
                    if not table_text or table_text == last_text:
                        continue
                    collected_texts.append(table_text)
                    last_text = table_text
                elif child.name == "div":
                    # Some publishers (e.g. baolaocai.vn) render paragraphs as bare <div> nodes.
                    # Treat leaf-ish divs (no nested block-ish tags) as paragraph candidates.
                    if child.find(tuple(blockish_tags - {"div"})):
                        queue.append(child)
                        continue
                    text = child.get_text(" ", strip=True)
                    text = _normalize_whitespace(text)
                    if not text or _contains_excluded_text(text) or text == last_text:
                        continue
                    collected_texts.append(text)
                    last_text = text
                else:
                    queue.append(child)

        if not collected_texts:
            return None
        collected_texts = _filter_domain_content(self.domain, collected_texts)
        if not collected_texts:
            return None
        return "\n\n".join(collected_texts)

    def _find_main_container(self, soup: BeautifulSoup):
        if self.site_config:
            for selector in self.site_config.main_container_selectors:
                elements = soup.select(selector)
                if not elements:
                    continue
                if len(elements) == 1:
                    return elements[0]
                best_element: Tag | None = None
                best_length = 0
                for element in elements:
                    if _is_in_excluded_section(element):
                        continue
                    text_length = len(element.get_text(" ", strip=True))
                    if text_length > best_length:
                        best_length = text_length
                        best_element = element
                if best_element:
                    return best_element

        selectors = [
            "[itemprop='articleBody']",
            "article",
            "section[itemtype*='Article']",
            "div[class*='article-body']",
            "section[class*='article-body']",
            "div[class*='entry']",
            "div[class*='content'], section[class*='content']",
        ]

        best_element: Tag | None = None
        best_length = 0
        for selector in selectors:
            for element in soup.select(selector):
                if _is_in_excluded_section(element):
                    continue
                text_length = len(element.get_text(" ", strip=True))
                if text_length > best_length:
                    best_length = text_length
                    best_element = element
        if best_element:
            return best_element

        if self.site_config and self.site_config.main_container_keywords:
            candidate = _find_largest_element_by_keyword(soup, self.site_config.main_container_keywords)
            if candidate:
                return candidate

        return None

    def _prune_main_container(self, container: Tag | None) -> Tag | None:
        if not container or not self.site_config:
            return container
        selectors = self.site_config.excluded_section_selectors
        if not selectors:
            return container

        for selector in selectors:
            for element in list(container.select(selector)):
                if element is container:
                    continue
                element.decompose()
        return container

    def _extract_category(self, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
        category_meta = soup.select_one("meta[property='article:section'], meta[name='article:section']")
        category_name = category_meta["content"].strip() if category_meta and category_meta.get("content") else None

        explicit_category_id: str | None = None

        if self.site_config:
            for extractor_name in self.site_config.category_extractors:
                extractor = _CATEGORY_EXTRACTORS.get(extractor_name)
                if not extractor:
                    logger.debug("Unknown category extractor '%s' for %s", extractor_name, self.domain)
                    continue
                resolved_id, resolved_name = extractor(self.base_url, soup)
                if resolved_id:
                    explicit_category_id = resolved_id
                if resolved_name:
                    category_name = resolved_name

        if not category_name:
            titlecate = soup.select_one("div.titlecate h1")
            if titlecate:
                link_texts = [
                    _normalize_whitespace(link.get_text(" ", strip=True))
                    for link in titlecate.find_all("a")
                    if _normalize_whitespace(link.get_text(" ", strip=True))
                ]
                if link_texts:
                    category_name = " > ".join(link_texts)
                else:
                    text_value = _normalize_whitespace(titlecate.get_text(" ", strip=True))
                    if text_value:
                        category_name = text_value.replace(">", " > ")

        if not category_name and explicit_category_id:
            category_name = _prettify_slug(explicit_category_id)

        category_id = explicit_category_id or (_slugify(category_name) if category_name else None)
        return category_id, category_name

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        selectors = [
            ".article__author",
            ".article-author",
            "[itemprop='author']",
            ".author-name",
            "meta[name='author']",
            "meta[property='article:author']",
        ]
        for selector in selectors:
            element = soup.select_one(selector)
            if not element:
                continue
            if element.name == "meta":
                content = element.get("content")
                if content and content.strip():
                    return _normalize_whitespace(content)
            else:
                text = element.get_text(" ", strip=True)
                text = _normalize_whitespace(text)
                if text:
                    return text
        return None

    def _extract_tags(self, soup: BeautifulSoup) -> str | None:
        tags: List[str] = []
        for meta_tag in soup.select("meta[property='article:tag']"):
            if meta_tag.get("content"):
                content = meta_tag["content"].strip()
                if not content:
                    continue
                if "," in content:
                    for part in content.split(","):
                        part = part.strip()
                        if part:
                            tags.append(part)
                else:
                    tags.append(content)

        keywords_meta = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.IGNORECASE)})
        if keywords_meta and keywords_meta.get("content"):
            keywords = [kw.strip() for kw in keywords_meta["content"].split(",") if kw.strip()]
            tags.extend(keywords)

        tag_selectors = [
            "a[rel='tag']",
            ".tags a",
            ".tag-list a",
            ".article-tags a",
            "ul[class*='tag'] a",
            "li[class*='tag'] a",
            "div.block_tag a",
            "a.tag_item",
            "[class*='keyword'] a",
            ".c-widget-tags a",
            ".onecms__tags a",
        ]
        for selector in tag_selectors:
            for element in soup.select(selector):
                text = element.get_text(strip=True)
                if not text and element.get("title"):
                    text = element["title"].strip()
                if text:
                    tags.append(text)

        if self.site_config:
            for extractor_name in self.site_config.tag_extractors:
                extractor = _TAG_EXTRACTORS.get(extractor_name)
                if not extractor:
                    logger.debug("Unknown tag extractor '%s' for %s", extractor_name, self.domain)
                    continue
                tags.extend(extractor(soup))

        if not tags:
            return None
        tags = _deduplicate_preserve_order(tags)
        return ",".join(tags)

    def _extract_publish_date(self, soup: BeautifulSoup) -> datetime | None:
        selectors = [
            ("meta[property='article:published_time']", "content"),
            ("meta[name='pubdate']", "content"),
            ("meta[name='timestamp']", "content"),
            ("meta[itemprop='datePublished']", "content"),
            ("time[itemprop='datePublished']", "datetime"),
            ("time[datetime]", "datetime"),
            ("meta[property='og:updated_time']", "content"),
        ]
        for selector, attr in selectors:
            element = soup.select_one(selector)
            if element and element.get(attr):
                parsed = _parse_datetime(element[attr])
                if parsed:
                    return parsed
        jsonld_date = _extract_date_from_jsonld(soup)
        if jsonld_date:
            return jsonld_date

        attribute_candidates = ["data-date", "data-time", "data-published", "datetime"]
        for element in soup.select("[data-date], [data-time], [data-published]"):
            for attr in attribute_candidates:
                if element.get(attr):
                    parsed = _parse_datetime(element[attr])
                    if parsed:
                        return parsed

        text_selectors = [
            "span[id*='lblDate']",
            "span[class*='date']",
            "span[class*='time']",
            "div[class*='date']",
            "div[class*='time']",
            ".post-date",
            ".publish-date",
            ".detail-time",
            ".article__meta-time",
            ".meta-time",
            ".entry-date",
            ".date-post",
            ".time-post",
            ".c-time",
        ]
        for selector in text_selectors:
            for element in soup.select(selector):
                text = element.get_text(" ", strip=True)
                if not text:
                    continue
                parsed = _parse_datetime_text(text)
                if parsed:
                    return parsed
        return None

    def _extract_last_modified(self, soup: BeautifulSoup) -> datetime | None:
        selectors = [
            ("meta[property='article:modified_time']", "content"),
            ("meta[name='lastmod']", "content"),
            ("meta[name='last-modified']", "content"),
            ("time[itemprop='dateModified']", "datetime"),
            ("time[datetime][itemprop='dateModified']", "datetime"),
        ]
        for selector, attr in selectors:
            element = soup.select_one(selector)
            if element and element.get(attr):
                parsed = _parse_datetime(element[attr])
                if parsed:
                    return parsed
        return None

    def _extract_media_urls(
        self,
        soup: BeautifulSoup,
        selectors: Sequence[str],
        attr: str,
        skip_predicate: Optional[Callable[[str], bool]] = None,
    ) -> List[str]:
        urls: List[str] = []
        for selector in selectors:
            for element in soup.select(selector):
                if not element.get(attr):
                    continue
                media_url = element[attr].strip()
                if not media_url:
                    continue
                resolved_url = self._absolutize(media_url)
                if skip_predicate and skip_predicate(resolved_url):
                    continue
                urls.append(resolved_url)
        return urls

    def _extract_inline_images(
        self,
        soup: BeautifulSoup,
        container: Tag | None = None,
        *,
        extra_scopes: Sequence[Tag] = (),
    ) -> List[str]:
        urls: List[str] = []
        scopes: List[Tag] = []
        seen_scope_ids: set[int] = set()
        for scope in list(extra_scopes) + self._resolve_inline_image_scopes(soup, container):
            scope_id = id(scope)
            if scope_id in seen_scope_ids:
                continue
            seen_scope_ids.add(scope_id)
            scopes.append(scope)
        allow_extensionless_images = self._allow_extensionless_images()

        for scope in scopes:
            if container is None and scope is soup:
                image_tags = soup.select(
                    "article img, div[class*='article'] img, div[class*='content'] img"
                )
            else:
                image_tags = scope.find_all("img")

            for img in image_tags:
                if _is_in_excluded_section(img) or _has_class_in_ancestors(
                    img, "i-con-gg-news"
                ) or _has_class_in_ancestors(img, "gg-news"):
                    continue
                selected: str | None = None
                for candidate in _collect_image_candidates(img):
                    resolved = self._absolutize(candidate)
                    if self._should_skip_image_url(
                        resolved, allow_extensionless=allow_extensionless_images
                    ):
                        continue
                    selected = resolved
                    break
                if selected:
                    urls.append(selected)

        for scope in scopes:
            if container is None and scope is soup:
                source_tags = soup.select("picture source, source[type*='image']")
            else:
                source_tags = scope.find_all("source")

            for source_tag in source_tags:
                if _is_in_excluded_section(source_tag) or _has_class_in_ancestors(
                    source_tag, "i-con-gg-news"
                ) or _has_class_in_ancestors(source_tag, "gg-news"):
                    continue
                selected: str | None = None
                for candidate in _collect_image_candidates(source_tag):
                    resolved = self._absolutize(candidate)
                    if self._should_skip_image_url(
                        resolved, allow_extensionless=allow_extensionless_images
                    ):
                        continue
                    selected = resolved
                    break
                if selected:
                    urls.append(selected)

        for scope in scopes:
            for element in scope.select("[style*='background']"):
                if _is_in_excluded_section(element) or _has_class_in_ancestors(
                    element, "i-con-gg-news"
                ) or _has_class_in_ancestors(element, "gg-news"):
                    continue
                for candidate in _extract_urls_from_style(element.get("style", "")):
                    resolved = self._absolutize(candidate)
                    if self._should_skip_image_url(
                        resolved, allow_extensionless=allow_extensionless_images
                    ):
                        continue
                    urls.append(resolved)
        return urls

    def _should_skip_image_url(self, url: str, *, allow_extensionless: bool = False) -> bool:
        if not url:
            return True
        if self.site_config and self.site_config.excluded_image_urls:
            lowered = url.lower().strip()
            for excluded in self.site_config.excluded_image_urls:
                if not excluded:
                    continue
                if lowered == excluded.lower().strip():
                    return True
        return _should_skip_image_url(url, allow_extensionless=allow_extensionless)

    def _resolve_inline_image_scopes(self, soup: BeautifulSoup, container: Tag | None) -> List[Tag]:
        if container is None:
            return [soup]
        if not self.site_config:
            return [container]
        selectors = self.site_config.inline_image_container_selectors
        if not selectors:
            return [container]

        scopes: List[Tag] = []
        include_container = False
        for selector in selectors:
            normalized = selector.strip()
            if not normalized:
                continue
            search_root = container
            if normalized.startswith("soup:"):
                include_container = True
                normalized = normalized[5:].strip()
                if not normalized:
                    continue
                search_root = soup
            scopes.extend(search_root.select(normalized))
        if include_container and container not in scopes:
            # Ensure primary content stays in scope when adding soup-level selectors.
            scopes.append(container)
        if not scopes:
            return [container]
        return scopes

    def _extract_inline_videos(self, soup: BeautifulSoup, container: Tag | None = None) -> List[str]:
        urls: List[str] = []
        search_space = container if container is not None else soup

        def append_from_tag(tag: Tag) -> None:
            for candidate in _collect_video_candidates(tag):
                if _should_skip_video_candidate(candidate):
                    continue
                resolved = self._absolutize(candidate)
                if _should_skip_video_candidate(resolved):
                    continue
                urls.append(resolved)

        for video in search_space.find_all("video"):
            append_from_tag(video)
            for source in video.find_all("source"):
                append_from_tag(source)

        for element in search_space.find_all(True):
            if element.name == "video":
                continue
            if not any(attr in element.attrs for attr in _VIDEO_WRAPPER_ATTRS):
                continue
            append_from_tag(element)

        return urls

    def _absolutize(self, href: str) -> str:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        return urljoin(self.base_url, href)

    def _allow_extensionless_images(self) -> bool:
        return bool(self.site_config and self.site_config.allow_extensionless_images)


MAX_TAG_LENGTH = 500




def _first_text(soup: BeautifulSoup, selectors: Sequence[str]) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        # logger.info("element %s", element)
        if element:
            if element.name == "meta":
                content = element.get("content")
                if content:
                    return content.strip()
            else:
                text = element.get_text(strip=True)
                if text:
                    return text
    return None


_PARAGRAPH_WRAP_RE = re.compile(r"^<p\b[^>]*>(?P<inner>.*)</p>$", re.IGNORECASE | re.DOTALL)


def _clean_description_text(text: str) -> str | None:
    cleaned = _strip_wrapping_paragraph_tags(text)
    cleaned = cleaned.strip()
    return cleaned or None


def _strip_wrapping_paragraph_tags(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return trimmed
    match = _PARAGRAPH_WRAP_RE.match(trimmed)
    if match:
        inner = match.group("inner")
        return inner.strip()
    return value


def _join_paragraphs(elements: Iterable) -> str | None:
    texts: List[str] = []
    for element in elements:
        text = element.get_text(" ", strip=True)
        if text:
            texts.append(text)
    if not texts:
        return None
    return "\n\n".join(texts)


def _extract_moha_article_id(url: str) -> str | None:
    match = _MOHA_ARTICLE_ID_RE.search(url)
    if not match:
        return None
    return match.group("id")


def _moha_html_has_content(html: str) -> bool:
    if not html:
        return False
    soup = _make_soup(html)
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


def _should_use_moha_api(url: str, html: str) -> bool:
    if not _extract_moha_article_id(url):
        return False
    domain = urlparse(url).netloc.lower()
    if not (domain == "moha.gov.vn" or domain.endswith(".moha.gov.vn")):
        return False
    if "<div id=\"root\"></div>" in html:
        return True
    return not _moha_html_has_content(html)


def _render_moha_article_html(payload: dict[str, Any] | None) -> str | None:
    if not payload or not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None

    title = data.get("TieuDe") or ""
    description_html = data.get("MoTa") or ""
    content_html = data.get("NoiDung") or ""
    category = None
    if isinstance(data.get("ChuyenMuc"), dict):
        category = data["ChuyenMuc"].get("TenChuyenMuc")
    published_at = data.get("NgayXuatBan")

    description_text = ""
    if description_html:
        description_text = _make_soup(description_html).get_text(" ", strip=True)

    head_parts = [
        "<meta charset=\"utf-8\" />",
        f"<meta name=\"title\" content=\"{escape(title)}\" />" if title else "",
        f"<meta name=\"description\" content=\"{escape(description_text)}\" />"
        if description_text
        else "",
        f"<meta property=\"article:section\" content=\"{escape(category)}\" />"
        if category
        else "",
        f"<meta property=\"article:published_time\" content=\"{escape(published_at)}\" />"
        if published_at
        else "",
    ]

    body_parts = [
        "<article class=\"moha-article\">",
        f"<h1 class=\"moha-article__title\">{escape(title)}</h1>" if title else "",
        f"<div class=\"moha-article__desc\">{description_html}</div>" if description_html else "",
        f"<div class=\"moha-article__content\">{content_html}</div>" if content_html else "",
        "</article>",
    ]

    head = "".join(part for part in head_parts if part)
    body = "".join(part for part in body_parts if part)
    return f"<!doctype html><html><head>{head}</head><body>{body}</body></html>"


def _parse_mof_article_content(raw: Any) -> tuple[str | None, dict[str, Any]]:
    if not raw:
        return None, {}
    payload: dict[str, Any] | None = None
    if isinstance(raw, dict):
        payload = raw
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw, {}
        if isinstance(parsed, dict):
            payload = parsed
    if payload is None:
        return None, {}
    content_html = payload.get("Content")
    return content_html, payload


def _render_mof_article_html(payload: dict[str, Any] | None) -> str | None:
    if not payload or not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None

    title = data.get("title") or ""
    description = data.get("description") or ""
    author = data.get("author") or ""
    published_at = data.get("publicationTime") or ""
    category_name = None
    category_data = data.get("articleCategory")
    if isinstance(category_data, dict):
        category_name = category_data.get("name")

    content_html, content_payload = _parse_mof_article_content(
        data.get("articleContent")
    )
    content_parts: List[str] = []
    if content_html:
        content_parts.append(content_html)

    attachment_link = content_payload.get("Link") if content_payload else None
    attachment_name = content_payload.get("FileName") or content_payload.get("Title")
    if attachment_link:
        link_text = attachment_name or "Tai lieu"
        content_parts.append(
            f"<p><a href=\"{escape(str(attachment_link))}\">{escape(str(link_text))}</a></p>"
        )

    attachments = data.get("attachments")
    attachment_items: List[str] = []
    if isinstance(attachments, list):
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            link = attachment.get("link")
            name = attachment.get("name") or "Tai lieu"
            if not link:
                continue
            attachment_items.append(
                f"<li><a href=\"{escape(str(link))}\">{escape(str(name))}</a></li>"
            )
    if attachment_items:
        content_parts.append(
            "<ul class=\"mof-article__attachments\">"
            + "".join(attachment_items)
            + "</ul>"
        )

    source = data.get("source") or ""
    source_link = data.get("sourceLink") or ""
    if source or source_link:
        source_label = escape(str(source)) if source else "Nguon"
        if source_link:
            content_parts.append(
                f"<p class=\"mof-article__source\"><a href=\"{escape(str(source_link))}\">{source_label}</a></p>"
            )
        else:
            content_parts.append(f"<p class=\"mof-article__source\">{source_label}</p>")

    description_text = ""
    if description:
        description_text = _make_soup(description).get_text(
            " ", strip=True
        )

    image_link = data.get("imageLink") or ""
    head_parts = [
        "<meta charset=\"utf-8\" />",
        f"<meta name=\"title\" content=\"{escape(title)}\" />" if title else "",
        f"<meta name=\"description\" content=\"{escape(description_text)}\" />"
        if description_text
        else "",
        f"<meta property=\"article:section\" content=\"{escape(category_name)}\" />"
        if category_name
        else "",
        f"<meta property=\"article:published_time\" content=\"{escape(published_at)}\" />"
        if published_at
        else "",
        f"<meta name=\"author\" content=\"{escape(author)}\" />" if author else "",
    ]
    if image_link and not image_link.endswith("/images/noimage.png"):
        head_parts.append(
            f"<meta property=\"og:image\" content=\"{escape(image_link)}\" />"
        )

    tags = data.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            value = None
            if isinstance(tag, str):
                value = tag.strip()
            elif isinstance(tag, dict):
                value = str(tag.get("name") or "").strip()
            if value:
                head_parts.append(
                    f"<meta property=\"article:tag\" content=\"{escape(value)}\" />"
                )

    body_parts = [
        "<article class=\"mof-article\">",
        f"<h1 class=\"mof-article__title\">{escape(title)}</h1>" if title else "",
        f"<div class=\"mof-article__desc\">{escape(description)}</div>"
        if description
        else "",
        "<div class=\"mof-article__content\">",
        "".join(content_parts),
        "</div>",
        "</article>",
    ]

    head = "".join(part for part in head_parts if part)
    body = "".join(part for part in body_parts if part)
    return f"<!doctype html><html><head>{head}</head><body>{body}</body></html>"


def _parse_datetime(value: str) -> Optional[datetime]:
    try:
        parsed = date_parser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc)
    return parsed


def _deduplicate_preserve_order(items: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _contains_excluded_text(element_or_text) -> bool:
    if isinstance(element_or_text, Tag):
        text = element_or_text.get_text(" ", strip=True)
    else:
        text = str(element_or_text)
    lowered = text.lower()
    excluded_keywords = [
        "chia sẻ facebook",
        "theo dõi trên",
        "bình luận của bạn",
        "ban biên tập",
        "số người thích",
        "sponsored",
        "quảng cáo",
    ]
    if any(keyword in lowered for keyword in excluded_keywords):
        return True

    normalized = lowered.strip()
    time_prefixes = (
        "thời gian",
        "thoi gian",
    )
    if any(normalized.startswith(prefix) for prefix in time_prefixes):
        # Short metadata snippets like "Thời gian: 09:00" should be filtered,
        # but keep longer editorial sentences that merely mention "thời gian".
        return len(normalized) <= 60
    return False


def _truncate_tag_list(value: str | None, max_length: int) -> str | None:
    if not value:
        return None
    if len(value) <= max_length:
        return value

    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return value[:max_length]

    truncated: List[str] = []
    current_length = 0
    for part in parts:
        addition = len(part) if not truncated else len(part) + 1  # include comma
        if current_length + addition > max_length:
            break
        truncated.append(part)
        current_length += addition

    if not truncated:
        return value[:max_length]
    return ",".join(truncated)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _table_to_text(table: Tag) -> str | None:
    rows: List[str] = []
    for tr in table.find_all("tr"):
        cells = []
        for cell in tr.find_all(["th", "td"]):
            cell_text = _normalize_whitespace(cell.get_text(" ", strip=True))
            if cell_text:
                cells.append(cell_text)
        if cells:
            rows.append(" | ".join(cells))
    if not rows:
        return None
    return "\n".join(rows)


def _tokenize_identifier(value: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


_EXCLUDED_SECTION_TOKENS = {
    "ads",
    "advert",
    "banner",
    "sponsor",
    "relationship",
    "related",
    "relate",
    "tinlienquan",
    "innerarticle",
    "share",
    "social",
    "comment",
    "promo",
    "widget",
    "tags",
    "tagbox",
    "taglist",
    "keyword",
    "subscribe",
    "breadcrumb",
}


def _has_excluded_marker(element: Tag) -> bool:
    attribute_names = [
        "class",
        "id",
        "data-role",
        "data-component",
        "data-block",
        "data-type",
    ]
    for attr_name in attribute_names:
        attr_value = element.get(attr_name)
        if not attr_value:
            continue
        values = attr_value if isinstance(attr_value, list) else [attr_value]
        for value in values:
            if "box-adv" in str(value).lower():
                return True
            tokens = _tokenize_identifier(value)
            if any(
                token == keyword or token.startswith(keyword)
                for token in tokens
                for keyword in _EXCLUDED_SECTION_TOKENS
            ):
                return True
    return False


def _is_in_excluded_section(element: Tag) -> bool:
    current = element
    while isinstance(current, Tag):
        if _has_excluded_marker(current):
            return True
        current = current.parent
    return False


def _has_class_in_ancestors(element: Tag, class_name: str) -> bool:
    current = element
    while isinstance(current, Tag):
        classes = current.get("class") or []
        if class_name in classes:
            return True
        current = current.parent
    return False


def _filter_domain_content(domain: str, segments: List[str]) -> List[str]:
    normalized_domain = domain.lower()
    if normalized_domain.endswith("cafebiz.vn"):
        filtered: List[str] = []
        for text in segments:
            normalized = text.strip()
            lowered = normalized.lower()
            if not normalized:
                continue
            if normalized.startswith("Đáng chú ý") and (len(filtered) >= 3 or "CEO" in normalized or "Tin vui" in normalized or "Vươn Mình" in normalized):
                break
            if "lượt xem" in lowered:
                continue
            if lowered.startswith("theo "):
                # Allow real editorial sentences such as "Theo Bộ NN&PTNT, ..."
                # but skip short credit lines like "Theo VTV" or "Theo CafeBiz".
                stripped = normalized.rstrip(".: ")
                if "," not in stripped and len(stripped.split()) <= 8:
                    continue
            filtered.append(text)
        return filtered
    if normalized_domain.endswith("moit.gov.vn"):
        filtered = []
        seen: set[str] = set()
        for text in segments:
            normalized = _normalize_whitespace(text)
            if not normalized:
                continue
            cleaned = normalized.replace("Đọc bài", "").replace("Copy link", "")
            cleaned = _normalize_whitespace(cleaned)
            lowered = cleaned.lower()
            if not cleaned:
                continue
            if lowered in ("đọc bài", "copy link"):
                continue
            if lowered.startswith("tags:") or lowered.startswith("tag:"):
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            filtered.append(cleaned)
        return filtered
    return segments


def _extract_date_from_jsonld(soup: BeautifulSoup) -> Optional[datetime]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("datePublished", "dateCreated", "dateModified"):
                if item.get(key):
                    parsed = _parse_datetime(item[key])
                    if parsed:
                        return parsed
    return None


def _parse_datetime_text(text: str) -> Optional[datetime]:
    cleaned = text.strip()
    if not cleaned:
        return None
    try:
        parsed = date_parser.parse(cleaned, fuzzy=True, dayfirst=True)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc)
    return parsed


def _slugify(value: str | None) -> str | None:
    if not value:
        return None
    normalized = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    tokens = re.findall(r"[a-z0-9]+", stripped.lower())
    if not tokens:
        return None
    slug = "_".join(tokens)
    if len(slug) <= 100:
        return slug
    digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8]
    allowed = max(1, 100 - len(digest) - 1)
    trimmed = slug[:allowed].rstrip("_")
    if not trimmed:
        trimmed = slug[:allowed]
    return f"{trimmed}_{digest}"


_STYLE_URL_RE = re.compile(r"url\((['\"]?)(.+?)\1\)")
_IMAGE_PLACEHOLDER_KEYWORDS = {
    "logo",
    "placeholder",
    "default",
    "banner",
    "ads",
    "adserver",
    "icon",
    "sprite",
    "nophoto",
    "no-photo",
    "blank",
    "spacer",
    "tracking",
    "pixel",
}


def _collect_image_candidates(tag: Tag) -> List[str]:
    candidates: List[str] = []
    attr_names = [
        "src",
        "data-src",
        "data-original",
        "data-lazy-src",
        "data-medium-file",
        "data-large-file",
        "data-image",
        "data-fullsrc",
        "data-zoom-image",
        "data-highres",
    ]
    for attr_name in attr_names:
        value = tag.get(attr_name)
        if value:
            candidates.append(value)

    for attr_name in ("srcset", "data-srcset"):
        value = tag.get(attr_name)
        if value:
            candidates.extend(_parse_srcset(value))

    if tag.get("style"):
        candidates.extend(_extract_urls_from_style(tag["style"]))

    seen: set[str] = set()
    unique_candidates: List[str] = []
    for candidate in candidates:
        cleaned = candidate.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_candidates.append(cleaned)
    return unique_candidates


def _parse_srcset(value: str) -> List[str]:
    results: List[str] = []
    for part in value.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        url_only = stripped.split(" ")[0]
        if url_only:
            results.append(url_only.strip())
    return results


def _extract_urls_from_style(style: str) -> List[str]:
    if not style:
        return []
    matches = _STYLE_URL_RE.findall(style)
    return [match[1].strip() for match in matches if match[1].strip()]


def _should_skip_image_url(url: str, *, allow_extensionless: bool = False) -> bool:
    if not url:
        return True
    lowered = url.lower()
    if lowered.startswith("data:"):
        return True
    if "insert_random_number_here" in lowered:
        return True
    if "www/delivery" in lowered:
        return True

    parsed = urlparse(url)
    filename = posixpath.basename(parsed.path).lower()
    if filename == "grey.gif":
        return True
    if filename and any(keyword in filename for keyword in _IMAGE_PLACEHOLDER_KEYWORDS):
        return True
    extension = posixpath.splitext(parsed.path)[1].lower()
    if not extension or extension not in _ALLOWED_IMAGE_EXTENSIONS:
        if allow_extensionless and extension == "":
            return False
        return True
    if not filename and not parsed.netloc:
        return True
    return False


_URL_IN_TEXT_RE = re.compile(r"https?://[^\s'\"<>]+|//[^\s'\"<>]+")
_ALLOWED_IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".webd",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".avif",
)
_VIDEO_EXTENSIONS = (
    ".mp4",
    ".m3u8",
    ".mpd",
    ".webm",
    ".mov",
    ".m4v",
    ".flv",
    ".avi",
    ".wmv",
)

_VIDEO_ATTRIBUTE_NAMES = (
    "src",
    "data-src",
    "data-href",
    "data-url",
    "data-video",
    "data-video-src",
    "data-video-url",
    "data-video-sd",
    "data-video-hd",
    "data-default-src",
    "data-mp4",
    "data-file",
    "data-files",
    "data-source",
    "data-fluid-hd-src",
    "data-fluid-sd-src",
    "data-fluid-src",
    "data-fluid-source",
    "data-hls-src",
    "data-hls",
    "data-dash-src",
    "data-download",
    "data-stream",
    "data-stream-src",
    "data-playlist",
    "data-embed",
)

_VIDEO_WRAPPER_ATTRS = tuple(attr for attr in _VIDEO_ATTRIBUTE_NAMES if attr != "src")


def _collect_video_candidates(tag: Tag) -> List[str]:
    candidates: List[str] = []
    seen: set[str] = set()

    for attr_name in _VIDEO_ATTRIBUTE_NAMES:
        if attr_name not in tag.attrs:
            continue
        raw_value = tag.get(attr_name)
        values: List[str]
        if isinstance(raw_value, (list, tuple)):
            values = [str(item) for item in raw_value if item]
        elif raw_value is None:
            continue
        else:
            values = [str(raw_value)]

        for value in values:
            cleaned = unescape(value).strip()
            if not cleaned:
                continue
            if cleaned.startswith("//"):
                cleaned = f"https:{cleaned}"

            if cleaned.startswith("{") or cleaned.startswith("["):
                for extracted in _extract_urls_from_jsonish(cleaned):
                    normalized = extracted.strip()
                    if not normalized:
                        continue
                    if normalized.startswith("//"):
                        normalized = f"https:{normalized}"
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    candidates.append(normalized)
                continue

            matches = _URL_IN_TEXT_RE.findall(cleaned)
            if matches:
                for match in matches:
                    normalized = match.strip()
                    if normalized.startswith("//"):
                        normalized = f"https:{normalized}"
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    candidates.append(normalized)
                continue

            parts = re.split(r"[|;]", cleaned) if ("|" in cleaned or ";" in cleaned) else [cleaned]
            final_parts: List[str] = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if "," in part and "http" not in part:
                    final_parts.extend(p.strip() for p in part.split(",") if p.strip())
                else:
                    final_parts.append(part)

            for part in final_parts:
                candidate = part.strip()
                if not candidate:
                    continue
                if candidate.startswith("//"):
                    candidate = f"https:{candidate}"
                if candidate in seen:
                    continue
                seen.add(candidate)
                candidates.append(candidate)

    return candidates


def _extract_urls_from_jsonish(raw: str) -> List[str]:
    data = _load_json_script_loose(raw)
    if data is None:
        return []
    results: List[str] = []
    _collect_urls_from_structure(data, results)
    return results


def _collect_urls_from_structure(node: Any, results: List[str]) -> None:
    if isinstance(node, str):
        normalized = node.strip()
        if normalized:
            if normalized.startswith("//"):
                normalized = f"https:{normalized}"
            if _looks_like_video_url(normalized) and normalized not in results:
                results.append(normalized)
        return
    if isinstance(node, dict):
        for value in node.values():
            _collect_urls_from_structure(value, results)
        return
    if isinstance(node, (list, tuple, set)):
        for item in node:
            _collect_urls_from_structure(item, results)


def _looks_like_video_url(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith(("javascript:", "data:", "#")):
        return False
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        path = parsed.path
    else:
        path = value.split("?", 1)[0].split("#", 1)[0]
    extension = posixpath.splitext(path)[1].lower()
    if extension in _VIDEO_EXTENSIONS:
        return True
    if "m3u8" in lowered or "manifest.mpd" in lowered:
        return True
    return False


def _should_skip_video_candidate(value: str) -> bool:
    if not value:
        return True
    lowered = value.lower()
    if lowered.startswith(("javascript:", "data:", "#")):
        return True
    return not _looks_like_video_url(value)


def _is_direct_video_media_url(value: str) -> bool:
    lowered = (value or "").lower()
    if not lowered:
        return False
    if _looks_like_video_url(lowered):
        parsed = urlparse(lowered)
        path = parsed.path or ""
        extension = posixpath.splitext(path)[1].lower()
        if extension in _VIDEO_EXTENSIONS:
            return True
        # Handle cases where direct media URL is embedded in query params.
        query = parsed.query or ""
        if query and re.search(
            r"(?i)(?:^|[?&])(file|src|url|video)=([^&#]+\\.(?:mp4|m3u8|mpd|webm|mov|m4v|flv|avi|wmv))(?:[&#]|$)",
            f"?{query}",
        ):
            return True
    return False


def _filter_domain_video_urls(domain: str, videos: List[str]) -> List[str]:
    normalized_domain = (domain or "").lower()
    if normalized_domain.endswith("vietnamfinance.vn"):
        # VietnamFinance often exposes player/runtime URLs in DOM metadata.
        # Keep only direct media links to avoid broken "video_path" records.
        return [url for url in videos if _is_direct_video_media_url(url)]
    return videos


_TRAILING_COMMA_RE = re.compile(r",\s*([\]}])")


def _find_largest_element_by_keyword(soup: BeautifulSoup, keywords: Sequence[str]) -> Tag | None:
    """Return the element with the most text where id/class contains any keyword."""
    lowered_keywords = tuple(keyword.lower() for keyword in keywords)
    best_element: Tag | None = None
    best_length = 0

    for element in soup.find_all(True):
        if element.name in {"script", "style", "noscript", "iframe", "form"}:
            continue
        if _is_in_excluded_section(element):
            continue
        attributes: list[str] = []
        element_id = element.get("id")
        if isinstance(element_id, str):
            attributes.append(element_id)
        classes = element.get("class")
        if isinstance(classes, list):
            attributes.extend(str(value) for value in classes if isinstance(value, str))
        elif isinstance(classes, str):
            attributes.append(classes)

        attribute_text = " ".join(attributes).lower()
        if not attribute_text:
            continue
        if not any(keyword in attribute_text for keyword in lowered_keywords):
            continue

        text_value = _normalize_whitespace(element.get_text(" ", strip=True))
        if not text_value:
            continue
        text_length = len(text_value)
        if text_length > best_length:
            best_element = element
            best_length = text_length
    return best_element


def _extract_genk_category(article_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    breadcrumb_data: dict | None = None

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        data = _load_json_script_loose(script.string)
        if data is None:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                breadcrumb_data = item
                break
        if breadcrumb_data:
            break

    if not breadcrumb_data:
        return None, None

    elements = breadcrumb_data.get("itemListElement")
    if not isinstance(elements, list):
        return None, None

    normalized_article_url = article_url.split("?", 1)[0].rstrip("/")
    candidates: List[Tuple[str | None, str | None]] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        item = element.get("item")
        if isinstance(item, dict):
            url = item.get("@id") or item.get("item") or item.get("url")
            name = item.get("name")
        else:
            url = None
            name = element.get("name") if isinstance(element, dict) else None
        candidates.append((url, name))

    if not candidates:
        return None, None

    filtered: List[Tuple[str | None, str | None]] = []
    for url, name in candidates:
        if not url:
            continue
        normalized_url = str(url).strip()
        if not normalized_url:
            continue
        base = normalized_url.rstrip("/")
        if base in {"https://genk.vn", "http://genk.vn"}:
            continue
        if normalized_article_url and base == normalized_article_url:
            continue
        filtered.append((normalized_url, name))

    candidate_url, candidate_name = filtered[-1] if filtered else candidates[-1]
    slug = _slug_from_url(candidate_url) if candidate_url else None
    if candidate_name:
        normalized_name = _normalize_whitespace(unescape(str(candidate_name)))
        name_value = normalized_name or None
    else:
        name_value = None
    return slug, name_value


def _load_json_script_loose(raw: str | None):
    if not raw:
        return None
    unescaped = unescape(raw.strip())
    try:
        return json.loads(unescaped)
    except (json.JSONDecodeError, TypeError):
        sanitized = _strip_trailing_commas(unescaped)
        if sanitized == unescaped:
            return None
        try:
            return json.loads(sanitized)
        except (json.JSONDecodeError, TypeError):
            return None


def _strip_trailing_commas(value: str) -> str:
    previous = None
    current = value
    while previous != current:
        previous = current
        current = _TRAILING_COMMA_RE.sub(r"\1", current)
    return current


def _extract_kenh14_tags(soup: BeautifulSoup) -> List[str]:
    collected: List[str] = []
    for item in soup.select("li.kbwsli"):
        tag_name: str | None = None
        for attr in ["data-name", "data-title", "data-tag"]:
            raw_value = item.get(attr)
            if raw_value and isinstance(raw_value, str):
                normalized = _normalize_whitespace(raw_value)
                if normalized:
                    tag_name = normalized
                    break
        if not tag_name:
            link = item.find("a")
            if link:
                tag_name = _normalize_whitespace(link.get_text(" ", strip=True))
        if tag_name:
            collected.append(tag_name)
    return collected


def _extract_vneconomy_tags(soup: BeautifulSoup) -> List[str]:
    collected: List[str] = []
    seen: set[str] = set()
    containers = soup.select("div.box-keyword div.list-tag")
    if not containers:
        containers = soup.select("div.list-tag")
    for container in containers:
        for link in container.select("a.tag"):
            text = None
            span = link.find("span")
            if span:
                text = span.get_text(" ", strip=True)
            if not text:
                text = link.get_text(" ", strip=True)
            text = _normalize_whitespace(text)
            if not text or text in seen:
                continue
            seen.add(text)
            collected.append(text)
    return collected


def _extract_vietnamnet_tags(soup: BeautifulSoup) -> List[str]:
    collected: List[str] = []
    selectors = ["div.tag-cotnent", ".tag-cotnent", "div.tag-content", ".tag-content"]
    for selector in selectors:
        containers = soup.select(selector)
        if not containers:
            continue
        for container in containers:
            # Vietnamnet nests tags inside h3 elements; prefer those to avoid capturing helper text.
            heading_tags = container.select("h3")
            if heading_tags:
                for heading in heading_tags:
                    text = _normalize_whitespace(heading.get_text(" ", strip=True))
                    if not text and heading.get("title"):
                        text = _normalize_whitespace(heading["title"])
                    if text:
                        collected.append(text)
                    else:
                        link = heading.find("a")
                        if link:
                            text = _normalize_whitespace(link.get_text(" ", strip=True))
                            if not text and link.get("title"):
                                text = _normalize_whitespace(link["title"])
                            if text:
                                collected.append(text)
            else:
                for link in container.select("a[href]"):
                    text = _normalize_whitespace(link.get_text(" ", strip=True))
                    if not text and link.get("title"):
                        text = _normalize_whitespace(link["title"])
                    if text:
                        collected.append(text)
        if collected:
            break
    return collected


def _extract_baodaklak_tags(soup: BeautifulSoup) -> List[str]:
    collected: List[str] = []
    for link in soup.select("div.tag_list a[href]"):
        text = _normalize_whitespace(link.get_text(" ", strip=True))
        if text:
            collected.append(text)
    return collected


def _extract_kenh14_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    active_tab = soup.select_one("li.kbwsli.active")
    if active_tab:
        id_attr_candidates = [
            "data-id",
            "data-cat",
            "data-catid",
            "data-category",
            "data-categoryid",
            "data-cate",
            "data-cateid",
            "data-value",
        ]
        raw_id: str | None = None
        for attr in id_attr_candidates:
            raw_value = active_tab.get(attr)
            if raw_value and isinstance(raw_value, str):
                stripped = raw_value.strip()
                if stripped:
                    raw_id = stripped
                    break

        name_attr_candidates = ["data-name", "data-title"]
        category_name: str | None = None
        for attr in name_attr_candidates:
            raw_name = active_tab.get(attr)
            if raw_name and isinstance(raw_name, str):
                normalized_name = _normalize_whitespace(raw_name)
                if normalized_name:
                    category_name = normalized_name
                    break

        link = active_tab.find("a")
        if not category_name and link:
            category_name = _normalize_whitespace(link.get_text(" ", strip=True))

        category_id = raw_id
        if not category_id and link and link.get("href"):
            category_id = _slug_from_url(link["href"])

        if category_name or category_id:
            return category_id, category_name

    selectors = [
        "div.kbwc-meta a.kbwc__cate",
        "div.kbwc-meta a.kbwc-cate",
        "ul.kbwc-breadcrumb a",
        "ul.breadcrumb a",
        "nav.bread-crumb a",
        "li.breadcrumb-item a",
        ".kds-breadcrumb a",
    ]

    for selector in selectors:
        links = [
            link
            for link in soup.select(selector)
            if _normalize_whitespace(link.get_text(" ", strip=True))
        ]
        if not links:
            continue

        for link in reversed(links):
            name_text = _normalize_whitespace(link.get_text(" ", strip=True))
            if not name_text:
                continue
            href = (link.get("href") or "").strip()
            slug = _slug_from_url(href)
            if slug:
                return slug, name_text
        # fall back to the last link name even when slug missing
        name_text = _normalize_whitespace(links[-1].get_text(" ", strip=True))
        if name_text:
            return None, name_text
    return None, None


def _extract_baocamau_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    def _clean_slug(value) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    def _find_name_for_slug(slug: str | None) -> str | None:
        if not slug:
            return None
        normalized_slug = slug.strip("/").lower()
        candidate_selectors = [
            f".category-title-box a[href*='/{normalized_slug}/']",
            f"a[href*='/{normalized_slug}/']",
        ]
        for selector in candidate_selectors:
            for link in soup.select(selector):
                href = (link.get("href") or "").lower()
                if f"/{normalized_slug}/" not in href:
                    continue
                text = _normalize_whitespace(link.get_text(" ", strip=True))
                if text:
                    return text
        return None

    main_slug: str | None = None
    sub_slug: str | None = None
    input_element = soup.select_one("input[name='dataPostComment']")
    if input_element and input_element.get("value"):
        raw_value = input_element["value"]
        try:
            payload = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            payload = None
        if isinstance(payload, dict):
            main_slug = _clean_slug(payload.get("newsCate"))
            sub_slug = _clean_slug(payload.get("newsSubcate"))

    slug_to_use = sub_slug or main_slug
    main_name = _find_name_for_slug(main_slug)
    sub_name = _find_name_for_slug(sub_slug)

    if sub_slug and sub_name:
        category_name = f"{main_name} > {sub_name}" if main_name and main_name != sub_name else sub_name
    else:
        category_name = sub_name or main_name

    if not category_name:
        header_link = soup.select_one(".category-title-box .news-block-header span a")
        if header_link:
            text = _normalize_whitespace(header_link.get_text(" ", strip=True))
            if text:
                category_name = text
            if not slug_to_use:
                slug_to_use = _slug_from_url(header_link.get("href"))

    if slug_to_use:
        slug_to_use = slug_to_use.strip("/ ").lower()

    return slug_to_use, category_name


def _extract_baohaugiang_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one("div.box-breadcrumb")
    if not breadcrumb:
        return None, None
    link = breadcrumb.find("a", href=True)
    if link:
        name_text = _normalize_whitespace(link.get_text(" ", strip=True))
        slug = _slug_from_url(urljoin(base_url, link["href"]))
        return slug, name_text or None
    header = breadcrumb.find("h2")
    if not header:
        return None, None
    name_text = _normalize_whitespace(header.get_text(" ", strip=True))
    return _slugify(name_text), name_text


def _extract_cafebiz_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    link = soup.select_one("span.cat a[href]")
    if link is None:
        link = soup.select_one(".cat a[href]")

    if not link:
        return None, None

    category_name = _normalize_whitespace(link.get_text(" ", strip=True))
    if not category_name:
        title_attr = link.get("title")
        if title_attr and isinstance(title_attr, str):
            normalized_title = _normalize_whitespace(title_attr)
            if normalized_title:
                category_name = normalized_title

    category_id = _slug_from_url(link.get("href"))

    return category_id, category_name


def _extract_cafef_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    link = soup.select_one("a.category-page__name[data-role='cate-name']")
    if link is None:
        link = soup.select_one("a.category-page__name")

    if not link:
        mag_link = soup.select_one("a.sp-mag-logo[href*='emagazine'], a.sp-mag-logo, a[href*='emagazine.chn']")
        if mag_link:
            return "emagazine", "Emagazine"
        return None, None

    category_name = _normalize_whitespace(link.get_text(" ", strip=True))
    if not category_name:
        title_attr = link.get("title")
        if title_attr and isinstance(title_attr, str):
            normalized_title = _normalize_whitespace(title_attr)
            if normalized_title:
                category_name = normalized_title

    category_id = _slug_from_url(link.get("href"))

    return category_id, category_name


def _extract_tuoitre_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    # Top-level category link, e.g. <div class="detail-cate"><a href="/the-gioi.htm">Thế giới</a></div>
    link = soup.select_one("div.detail-cate a[href]")
    if not link:
        return None, None
    category_name = _normalize_whitespace(link.get_text(" ", strip=True)) or None
    return _slug_from_url(link.get("href")), category_name


def _extract_baodongkhoi_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    explicit_id: str | None = None
    category_name: str | None = None

    hidden_category = soup.select_one("input#txtnewscate")
    if hidden_category and hidden_category.get("value"):
        explicit_id = hidden_category["value"].strip().lower() or None

    link = soup.select_one("h2.catename-h1 a")
    if link:
        link_text = _normalize_whitespace(link.get_text(" ", strip=True))
        if link_text:
            category_name = link_text
        elif link.get("title"):
            category_name = _normalize_whitespace(link["title"])
        if not explicit_id:
            explicit_id = _slug_from_url(link.get("href"))

    return explicit_id, category_name


def _extract_baodongnai_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    selectors = (
        "div.breadcrumb a.title.fleft[href]",
        ".bread-crumb a.title.fleft[href]",
        "a.title.fleft[href]",
    )
    for selector in selectors:
        link = soup.select_one(selector)
        if not link:
            continue
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        href = link.get("href")
        category_id = _slug_from_url(urljoin(base_url, href)) if href else None
        if text_value or category_id:
            return category_id, text_value or None
    return None, None


def _extract_baodongthap_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one("div.breadcrumb-news-detail")
    if not breadcrumb:
        return None, None

    category_id: str | None = None
    category_name: str | None = None

    for link in breadcrumb.select("a[href]"):
        href = link.get("href")
        if href in (None, "", "/", "#"):
            continue
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if text_value.startswith(">"):
            text_value = text_value.lstrip(">").strip()
        if text_value:
            category_name = text_value
        slug = _slug_from_url(urljoin(base_url, href))
        if slug:
            category_id = slug

    if not category_id and not category_name:
        return None, None
    return category_id, category_name


def _extract_giadinh_suckhoedoisong_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    category_link = soup.select_one("a.category-page__name[data-role='cate-name']")
    if category_link is None:
        category_link = soup.select_one("a.category-page__name")

    category_name: str | None = None
    category_id: str | None = None

    if category_link:
        text_value = _normalize_whitespace(category_link.get_text(" ", strip=True))
        if text_value:
            category_name = text_value
        elif category_link.get("title"):
            title_text = _normalize_whitespace(category_link["title"])
            if title_text:
                category_name = title_text
        category_id = _slug_from_url(category_link.get("href"))

    return category_id, category_name


def _extract_soha_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    selectors = [
        "header a.nav-link.active",
        "header nav a.nav-link.active",
        "header .navbar-nav a.nav-link.active",
        "nav.navbar a.nav-link.active",
        ".navbar a.nav-link.active",
        ".nav-main a.nav-link.active",
        "a.nav-link.active",
    ]

    active_links: List[Tag] = []
    for selector in selectors:
        active_links = soup.select(selector)
        if active_links:
            break

    if not active_links:
        return None, None

    id_attr_candidates = [
        "data-id",
        "data-cateid",
        "data-category-id",
        "data-category",
        "data-catid",
        "data-cate",
        "data-value",
    ]

    for link in active_links:
        category_name = _normalize_whitespace(link.get_text(" ", strip=True))
        if not category_name:
            title_attr = link.get("title")
            if title_attr and isinstance(title_attr, str):
                category_name = _normalize_whitespace(title_attr)

        category_id: str | None = None
        for attr in id_attr_candidates:
            raw_value = link.get(attr)
            if raw_value and isinstance(raw_value, str):
                stripped = raw_value.strip()
                if stripped:
                    category_id = stripped
                    break
        if not category_id:
            category_id = _slug_from_url(link.get("href"))

        if category_name or category_id:
            return category_id, category_name

    return None, None


def _extract_baodautu_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    selectors = [
        "div.fs16.text-uppercase a[href]",
        ".fs16.text-uppercase a[href]",
        ".detail-cate a[href]",
    ]

    for selector in selectors:
        links = soup.select(selector)
        if not links:
            continue
        for link in links:
            text_value = _normalize_whitespace(link.get_text(" ", strip=True))
            if not text_value and link.get("title"):
                text_value = _normalize_whitespace(str(link["title"]))

            href = link.get("href")
            category_id = _slug_from_url(urljoin(base_url, href)) if href else None

            if category_id or text_value:
                return category_id, text_value

    return None, None


def _extract_mst_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    selectors = [
        "div.detail-top .detail-cate a[href]",
        "div.detail-cate a[href]",
    ]

    category_links: List[Tag] = []
    for selector in selectors:
        category_links = soup.select(selector)
        if category_links:
            break

    if not category_links:
        return None, None

    category_names: List[str] = []
    category_id: str | None = None

    for idx, link in enumerate(category_links):
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text_value and link.get("title"):
            text_value = _normalize_whitespace(str(link["title"]))
        if text_value:
            category_names.append(text_value)

        href = link.get("href") if idx == len(category_links) - 1 else None
        if href:
            category_id = _slug_from_url(urljoin(base_url, href))

    category_name = " > ".join(category_names) if category_names else None
    if not category_id and category_name:
        category_id = _slugify(category_name)

    return category_id, category_name


def _extract_baophapluat_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one("section.breadcrumbs .grow")
    if breadcrumb is None:
        breadcrumb = soup.select_one("section.breadcrumbs")
    if breadcrumb is None:
        return None, None

    links = [link for link in breadcrumb.select("a[href]") if link.get("href")]
    if not links:
        return None, None

    category_names: List[str] = []
    category_id: str | None = None

    for link in links:
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text_value and link.get("title"):
            text_value = _normalize_whitespace(str(link["title"]))
        if text_value:
            category_names.append(text_value)

        href = link.get("href")
        slug = _slug_from_url(urljoin(base_url, href)) if href else None
        if slug:
            category_id = slug

    category_name = " > ".join(category_names) if category_names else None
    return category_id, category_name


def _extract_baoxaydung_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    selectors = [
        "a.detail-cate-top.category-name_ac[href]",
        ".detail-cate-top a.category-name_ac[href]",
        "a.detail-cate-top[href]",
        ".detail-cate-top a[href]",
        "a.category-name_ac[href]",
    ]

    for selector in selectors:
        links = soup.select(selector)
        if not links:
            continue
        for link in links:
            text_value = _normalize_whitespace(link.get_text(" ", strip=True))
            if not text_value and link.get("title"):
                title_text = _normalize_whitespace(link["title"])
                if title_text:
                    text_value = title_text

            href = link.get("href")
            category_id = _slug_from_url(urljoin(base_url, href)) if href else None

            if category_id or text_value:
                return category_id, text_value

    return None, None


def _extract_vtv_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    selectors = [
        "div.list-cate a[data-role='cate-name']",
        ".list-cate a[data-role='cate-name']",
        "div.list-cate a.category-name_ac",
        ".list-cate a.category-name_ac",
        ".list-cate a",
    ]
    category_links: List[Tag] = []
    for selector in selectors:
        category_links = soup.select(selector)
        if category_links:
            break

    if not category_links:
        return None, None

    category_names: List[str] = []
    category_id: str | None = None

    for link in category_links:
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text_value and link.get("title"):
            text_value = _normalize_whitespace(link["title"])
        if text_value:
            category_names.append(text_value)

        href = link.get("href")
        if href:
            slug = _slug_from_url(urljoin(base_url, href))
            if slug:
                category_id = slug

    category_name = " > ".join(category_names) if category_names else None
    return category_id, category_name


def _extract_vtvgov_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    """
    vtv.gov.vn (cổng thông tin) hiển thị mục tin theo dạng:
      <div class="title-content title-content-image">
        <h2><a title="TIN TỨC - SỰ KIỆN (nội bộ)">...</a></h2>
      </div>

    Đồng thời URL bài viết thường có dạng:
      /news/<category-slug>/<article-slug>
    """

    parsed = urlparse(base_url)
    path = parsed.path or "/"
    segments = [segment for segment in path.split("/") if segment]
    category_id: str | None = None
    if len(segments) >= 2 and segments[0].lower() == "news":
        category_id = segments[1].strip() or None

    category_name: str | None = None
    for selector in (
        "div.title-content.title-content-image h2 a",
        "div.title-content h2 a",
        "div.title-content-image h2 a",
    ):
        node = soup.select_one(selector)
        if not node:
            continue
        title_attr = _normalize_whitespace((node.get("title") or "").strip())
        text_value = _normalize_whitespace(node.get_text(" ", strip=True))
        category_name = title_attr or text_value or None
        if category_name:
            break

    if not category_name and category_id:
        category_name = _prettify_slug(category_id)

    return category_id, category_name


def _extract_twentyfourh_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    """
    Trích category cho 24h.com.vn từ breadcrumb.

    Breadcrumb có dạng:
      <nav class="cate-24h-foot-breadcrumb">
        <ul>
          <li><a href="/">Trang chủ</a></li>
          <li><a href="https://www.24h.com.vn/bong-da-c48.html">Bóng đá</a></li>
        </ul>
      </nav>
    """
    breadcrumb = soup.select_one("nav.cate-24h-foot-breadcrumb")
    if not breadcrumb:
        return None, None

    category_id: str | None = None
    category_name: str | None = None

    for link in breadcrumb.select("ul li a[href]"):
        href = (link.get("href") or "").strip()
        if not href or href == "/":
            continue
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text_value and link.get("title"):
            text_value = _normalize_whitespace(str(link["title"]))
        if not text_value:
            continue

        category_name = text_value
        category_id = _slug_from_url(urljoin(base_url, href))

    return category_id, category_name


def _extract_vietnamnet_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one("div.bread-crumb-detail")
    if breadcrumb is None:
        breadcrumb = soup.select_one(".bread-crumb-detail")

    if not breadcrumb:
        return None, None

    category_id: str | None = None
    category_name: str | None = None

    for link in breadcrumb.select("ul li a[href]"):
        if link.find("img"):
            continue
        href = link.get("href")
        if not href:
            continue
        normalized_href = href.strip()
        if not normalized_href or normalized_href == "/":
            continue

        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text_value and link.get("title"):
            text_value = _normalize_whitespace(link["title"])
        if not text_value:
            continue

        category_name = text_value
        category_id = _slug_from_url(urljoin(base_url, href))
        break

    return category_id, category_name


def _extract_dantri_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    breadcrumb_links = soup.select("a[data-content-name='article-breadcrumb']")
    if not breadcrumb_links:
        breadcrumb_links = soup.select("li.dt-font-Inter.dt-float-left a")

    category_id: str | None = None
    category_name: str | None = None

    for link in breadcrumb_links:
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text_value and link.get("title"):
            text_value = _normalize_whitespace(str(link["title"]))

        href = link.get("data-content-target") or link.get("href")
        if href:
            slug = _slug_from_url(urljoin(base_url, href))
            if slug:
                category_id = slug

        if text_value:
            category_name = text_value

    return category_id, category_name


def _extract_znews_category(base_url: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    """
    Trích category cho znews.vn từ header bài viết.

    Cấu trúc:
      <p class="the-article-category">
          <a href="https://znews.vn/kinh-doanh-tai-chinh.html"
             title="Kinh doanh"
             class="parent_cate">
             Kinh doanh
          </a>
      </p>
    """
    container = soup.select_one("p.the-article-category")
    if not container:
        return None, None

    link = container.find("a", href=True)
    if not link:
        return None, None

    text_value = _normalize_whitespace(link.get_text(" ", strip=True))
    if not text_value and link.get("title"):
        text_value = _normalize_whitespace(str(link["title"]))

    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not text_value:
        return None, None

    return category_id, text_value


def _extract_baobinhduong_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one("div.breadcrumb-news-detail")
    if not breadcrumb:
        return None, None

    category_id: str | None = None
    category_name: str | None = None

    for link in breadcrumb.select("a[href]"):
        href = link.get("href")
        if href in (None, "", "/", "#"):
            continue
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if text_value.startswith(">"):
            text_value = text_value.lstrip(">").strip()
        if text_value:
            category_name = text_value
        slug = _slug_from_url(urljoin(base_url, href))
        if slug:
            category_id = slug

    if not category_id and not category_name:
        return None, None
    return category_id, category_name


def _extract_baobacninhtv_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    link = soup.select_one("a.post-meta[href]")
    if not link:
        return None, None

    text_value = _normalize_whitespace(link.get_text(" ", strip=True))
    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not text_value:
        return None, None

    return category_id, text_value


def _extract_baotayninh_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one(
        "div.block-header-news-detail div.breadcrumb-news-detail"
    )
    if not breadcrumb:
        breadcrumb = soup.select_one("div.breadcrumb-news-detail")
    if not breadcrumb:
        return None, None

    category_id: str | None = None
    category_name: str | None = None

    for link in breadcrumb.select("a[href]"):
        href = link.get("href")
        if href in (None, "", "/", "#"):
            continue
        text_value = _normalize_whitespace(link.get_text(" ", strip=True))
        if text_value.startswith(">"):
            text_value = text_value.lstrip(">").strip()
        if text_value:
            category_name = text_value
        slug = _slug_from_url(urljoin(base_url, href))
        if slug:
            category_id = slug

    if not category_id and not category_name:
        return None, None
    return category_id, category_name


def _extract_baodaklak_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    link = soup.select_one("a.maincatetitle[href]")
    if not link:
        return None, None

    text_value = _normalize_whitespace(link.get_text(" ", strip=True))
    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not text_value:
        return None, None

    return category_id, text_value


def _extract_baodienbienphu_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    link = soup.select_one("#detail-news a[href*='/tin-tuc/']")
    if not link:
        return None, None

    text_value = _normalize_whitespace(link.get_text(" ", strip=True))
    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not text_value:
        return None, None

    return category_id, text_value


def _extract_baotuyenquang_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    container = soup.select_one("div.cate_title_1") or soup.select_one(".cate_title_1")
    link = None
    if container:
        link = container.select_one("h2 a.title, h2 a[href]")
    if not link:
        link = soup.select_one("h2 a.title, h2 a[href]")
    if not link:
        return None, None

    category_name = _normalize_whitespace(link.get_text(" ", strip=True)) or None
    category_id = None
    for cls in link.get("class", []):
        if re.fullmatch(r"[0-9a-fA-F]{32}", cls):
            category_id = cls.lower()
            break
    if not category_id:
        href = link.get("href")
        category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not category_name:
        return None, None
    return category_id, category_name


def _extract_baothainguyen_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    link = soup.select_one("a.title.color1[href]")
    if not link:
        return None, None

    text_value = _normalize_whitespace(link.get_text(" ", strip=True))
    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not text_value:
        return None, None

    return category_id or _slugify(text_value), text_value or None


def _extract_baosonla_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one("ul.breadcrumb")
    if not breadcrumb:
        return None, None

    link = breadcrumb.select_one("a.active[href]")
    if not link:
        links = breadcrumb.select("a[href]")
        link = links[-1] if links else None
    if not link:
        return None, None

    text_value = _normalize_whitespace(link.get_text(" ", strip=True))
    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not text_value:
        return None, None

    return category_id or _slugify(text_value), text_value or None


def _extract_bocongan_category(
    _: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    label_nodes = soup.select(
        "a[href*='/chuyen-muc/'] .text-bca-main-01.hover\\:text-bca-main-01"
    )
    if not label_nodes:
        label_nodes = soup.select("a[href*='/chuyen-muc/'] .text-bca-main-01")
    if label_nodes:
        for node in label_nodes:
            link = node.find_parent("a")
            if not link:
                continue
            category_name = _normalize_whitespace(node.get_text(" ", strip=True))
            category_id = _slug_from_url(link.get("href")) or _slugify(category_name)
            return category_id, category_name

    links = soup.select("a.text-bca-main-01.hover\\:text-bca-main-01")
    if not links:
        links = soup.select("a.text-bca-main-01")
    if not links:
        return None, None

    best_link = None
    for link in links:
        href = link.get("href") or ""
        if "/chuyen-muc/" in href:
            best_link = link
            break
    if not best_link:
        best_link = links[-1]

    category_name = _normalize_whitespace(best_link.get_text(" ", strip=True))
    category_id = _slug_from_url(best_link.get("href")) or _slugify(category_name)
    return category_id, category_name


def _extract_cand_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb = soup.select_one(".uk-breadcrumb")
    if not breadcrumb:
        return None, None

    links = breadcrumb.find_all("a", href=True)
    if not links:
        return None, None

    link = links[-1]
    category_name = _normalize_whitespace(link.get_text(" ", strip=True))
    href = link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not category_name:
        return None, None

    return category_id or _slugify(category_name), category_name


def _extract_qdnd_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    head = soup.select_one(".bgbrdm .brcrum-title .head")
    if not head:
        return None, None
    links = head.find_all("a", href=True)
    if not links:
        return None, None
    link_texts = [
        _normalize_whitespace(link.get_text(" ", strip=True))
        for link in links
        if _normalize_whitespace(link.get_text(" ", strip=True))
    ]
    category_name = " > ".join(link_texts) if link_texts else None

    last_link = links[-1]
    href = last_link.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not category_name:
        return None, None

    return category_id or _slugify(category_name), category_name


def _extract_mofa_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb_item = soup.select_one(
        "ol.breadcrumb li.last-item a[href], li.last-item[typeof='v:Breadcrumb'] a[href]"
    )
    if not breadcrumb_item:
        breadcrumb_links = soup.select("li[typeof='v:Breadcrumb'] a[href]")
        if breadcrumb_links:
            breadcrumb_item = breadcrumb_links[-1]
    if not breadcrumb_item:
        breadcrumb_links = soup.select(
            ".breadcrumb .breadcrumb-content a[href], .breadcrumb-content a[href]"
        )
        if breadcrumb_links:
            candidates = [
                link
                for link in breadcrumb_links
                if link.get("href") and link.get("href") != "/"
            ]
            breadcrumb_item = candidates[-1] if candidates else breadcrumb_links[-1]
    if not breadcrumb_item:
        return None, None

    category_name = _normalize_whitespace(
        breadcrumb_item.get_text(" ", strip=True)
    )
    href = breadcrumb_item.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not category_name:
        return None, None

    return category_id or _slugify(category_name), category_name


def _extract_baoquangninh_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    breadcrumb_links = soup.select(
        ".breadcrumbs ol.breadcrumb li a[href], .breadcrumb li a[href]"
    )
    if not breadcrumb_links:
        breadcrumb_links = soup.select(".breadcrumbs a[href], .breadcrumb a[href]")
    if not breadcrumb_links:
        return None, None

    breadcrumb_item = breadcrumb_links[-1]
    category_name = _normalize_whitespace(breadcrumb_item.get_text(" ", strip=True))
    href = breadcrumb_item.get("href")
    category_id = _slug_from_url(urljoin(base_url, href)) if href else None

    if not category_id and not category_name:
        return None, None

    return category_id or _slugify(category_name), category_name


def _extract_baoquangngai_inline_html(soup: BeautifulSoup) -> str | None:
    for script in soup.find_all("script"):
        if not script.string or "outputData" not in script.string:
            continue
        text = script.string
        html_match = _BAOQUANGNGAI_CONTENT_HTML_RE.search(text)
        if html_match:
            html = unescape(html_match.group("html").strip())
            if html:
                return html
        output_match = _BAOQUANGNGAI_OUTPUTDATA_RE.search(text)
        if output_match:
            raw = output_match.group("html")
            decoded = unescape(_decode_js_string(raw).strip())
            if decoded:
                return decoded
    return None


def _decode_js_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def _extract_baoquangngai_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    category_node = soup.select_one("p.category")
    if not category_node:
        return None, None
    category_name = _normalize_whitespace(category_node.get_text(" ", strip=True))
    if not category_name:
        return None, None
    category_link = category_node.find("a")
    category_id = None
    if category_link and category_link.get("href"):
        category_id = _slug_from_url(urljoin(base_url, category_link["href"]))
    return category_id or _slugify(category_name), category_name


def _extract_baoquangtri_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    canonical_node = soup.select_one("meta[property='og:url'], link[rel='canonical']")
    if not canonical_node:
        return None, None
    canonical_url = canonical_node.get("content") or canonical_node.get("href")
    if not canonical_url:
        return None, None
    parsed = urlparse(urljoin(base_url, canonical_url))
    parts = [segment for segment in (parsed.path or "").split("/") if segment]
    if not parts:
        return None, None
    return parts[0].lower(), None


def _extract_baokhanhhoa_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    canonical_node = soup.select_one("meta[property='og:url'], link[rel='canonical']")
    if not canonical_node:
        return None, None
    canonical_url = canonical_node.get("content") or canonical_node.get("href")
    if not canonical_url:
        return None, None
    parsed = urlparse(urljoin(base_url, canonical_url))
    parts = [segment for segment in (parsed.path or "").split("/") if segment]
    if not parts:
        return None, None
    return parts[0].lower(), None


def _extract_bvhttdl_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    """
    bvhttdl.gov.vn shows the current section/category as a header block:

      <h3 class="block-title title-upper">
        <a href="/van-hoa-doanh-nghiep.htm" title="Văn hóa doanh nghiệp">Văn hóa doanh nghiệp</a>
      </h3>
    """

    anchor = soup.select_one("h3.block-title.title-upper a[href]")
    if not anchor:
        return None, None
    category_name = _normalize_whitespace(anchor.get_text(" ", strip=True)) or None
    href = anchor.get("href")
    if not href:
        return None, category_name

    parsed = urlparse(urljoin(base_url, href))
    path = (parsed.path or "").strip("/")
    if not path:
        return None, category_name

    last_segment = path.split("/")[-1]
    if last_segment.lower().endswith(".htm"):
        last_segment = last_segment[: -len(".htm")]
    category_id = last_segment.strip().lower() or None

    if not category_id and category_name:
        category_id = _slugify(category_name)
    return category_id, category_name


def _extract_breadcrumb_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    """
    Extract category information from common breadcrumb structures.

    This is especially useful for portal/CMS sites (e.g. Liferay) where
    `article:section` metadata is not present.
    """

    container = soup.select_one(
        "nav[aria-label='breadcrumb'], nav.breadcrumb, ul.breadcrumb, ol.breadcrumb, .breadcrumb, .breadcrumbs"
    )
    if not container:
        return None, None

    crumbs: list[tuple[str | None, str | None]] = []

    nodes: list[Tag] = list(container.select("li")) or list(container.select("a, span"))
    for node in nodes:
        href = None
        if node.name == "a":
            href = node.get("href")
            text = _normalize_whitespace(node.get_text(" ", strip=True))
        else:
            anchor = node.find("a", href=True)
            href = anchor.get("href") if anchor else None
            text = _normalize_whitespace(node.get_text(" ", strip=True))

        if not text:
            continue
        lowered = text.lower()
        if lowered in {"home", "trang chủ", "trang chu"}:
            continue
        crumbs.append((href, text))

    if not crumbs:
        return None, None

    # Prefer the last crumb that is a link (the current article title is often not a link).
    candidate_href: str | None = None
    candidate_name: str | None = None
    for href, text in reversed(crumbs):
        if href:
            candidate_href = href
            candidate_name = text
            break

    if candidate_name and candidate_href:
        category_id = _slug_from_url(urljoin(base_url, candidate_href))
        return category_id or _slugify(candidate_name), candidate_name

    # If none are links, fall back to the 2nd last crumb (best-effort).
    if len(crumbs) >= 2:
        _, category_name = crumbs[-2]
        if category_name:
            return _slugify(category_name), category_name

    return None, None


def _extract_baoninhbinh_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    """
    Extract category from Báo Ninh Bình breadcrumb.

    Example:
    <ol class="... uppercase ...">
      <li><a href="https://baoninhbinh.org.vn">...</a></li>
      <li><a href="https://baoninhbinh.org.vn/chinh-tri">Chính trị</a></li>
      <li><a href="https://baoninhbinh.org.vn/xay-dung-dang">Xây dựng đảng</a></li>
    </ol>
    """

    # Newer layout: category list item with inline-flex classes.
    for link in soup.select("li.inline-flex.items-center.gap-1\\.5 a[href]"):
        href = link.get("href")
        text = _normalize_whitespace(link.get_text(" ", strip=True))
        if not href or not text:
            continue
        category_id = _slug_from_url(urljoin(base_url, href))
        return category_id or _slugify(text), text

    preferred_ols: list[Tag] = []
    for ol in soup.select("ol"):
        classes = set(ol.get("class") or [])
        if {"uppercase", "font-semibold", "w-max"}.issubset(classes):
            preferred_ols.append(ol)

    candidates = []
    for ol in preferred_ols or soup.select("ol"):
        links = [
            link
            for link in ol.select("a[href]")
            if link.get("href") and _normalize_whitespace(link.get_text(" ", strip=True))
        ]
        if len(links) < 2:
            continue
        has_home = any(
            link.get("href", "").rstrip("/").lower() == base_url.rstrip("/").lower()
            for link in links
        )
        if not has_home:
            continue
        candidates.append((ol, links))

    if not candidates:
        return None, None

    # Prefer the candidate with most links (likely the breadcrumb trail).
    _, links = max(candidates, key=lambda item: len(item[1]))

    for link in reversed(links):
        href = link.get("href")
        text = _normalize_whitespace(link.get_text(" ", strip=True))
        if not text or not href:
            continue
        lowered = text.lower()
        if lowered in {"home", "trang chủ", "trang chu"}:
            continue
        if href.rstrip("/").lower() == base_url.rstrip("/").lower():
            continue
        category_id = _slug_from_url(urljoin(base_url, href))
        return category_id or _slugify(text), text

    return None, None


def _extract_khoahocphattrien_category(
    base_url: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    """Extract category for khoahocphattrien.vn (tagdiv theme layout)."""

    link = soup.select_one("ul.td-category a[href], .td-category a[href]")
    if link:
        href = link.get("href")
        text = _normalize_whitespace(link.get_text(" ", strip=True))
        if text:
            if href:
                category_id = _slug_from_url(urljoin(base_url, href))
                return category_id or _slugify(text), text
            return _slugify(text), text

    container = soup.select_one(".entry-crumbs")
    if not container:
        return None, None

    crumbs: list[str] = []
    for node in container.select("a, span"):
        text = _normalize_whitespace(node.get_text(" ", strip=True))
        if not text:
            continue
        lowered = text.lower()
        if lowered in {"home", "trang chủ", "trang chu"}:
            continue
        crumbs.append(text)

    if not crumbs:
        return None, None

    category_name = crumbs[-1]
    return _slugify(category_name), category_name


def _extract_tapchitoaan_category(
    _: str, soup: BeautifulSoup
) -> Tuple[str | None, str | None]:
    """
    Extract category from tapchitoaan.vn.

    Example:
    <h6 class="cat-name">Dân sinh</h6>
    """

    label = soup.select_one("h6.cat-name")
    if not label:
        return None, None
    category_name = _normalize_whitespace(label.get_text(" ", strip=True))
    if not category_name:
        return None, None
    return _slugify(category_name), category_name


def _extract_eva_category(_: str, soup: BeautifulSoup) -> Tuple[str | None, str | None]:
    """
    Extract category from EVA breadcrumb list.

    Example:
      <ul class="d-flex align-items-center"> ... <li class="act"><a ...>Phong thủy</a></li>
    """

    breadcrumb = soup.select_one("ul.d-flex.align-items-center")
    if not breadcrumb:
        return None, None

    links = [
        link
        for link in breadcrumb.select("li a[href]")
        if _normalize_whitespace(link.get_text(" ", strip=True))
    ]
    if not links:
        return None, None

    # Prefer the last breadcrumb link (current section).
    for link in reversed(links):
        name_text = _normalize_whitespace(link.get_text(" ", strip=True))
        if not name_text:
            continue
        href = (link.get("href") or "").strip()
        slug = _slug_from_url(href)
        if slug:
            return slug, name_text

    # Fall back to last link name if slug missing.
    name_text = _normalize_whitespace(links[-1].get_text(" ", strip=True))
    if name_text:
        return None, name_text
    return None, None


_CATEGORY_EXTRACTORS: dict[str, Callable[[str, BeautifulSoup], Tuple[str | None, str | None]]] = {
    "genk_category": _extract_genk_category,
    "kenh14_category": _extract_kenh14_category,
    "cafebiz_category": _extract_cafebiz_category,
    "cafef_category": _extract_cafef_category,
    "tuoitre_category": _extract_tuoitre_category,
    "baocamau_category": _extract_baocamau_category,
    "baohaugiang_category": _extract_baohaugiang_category,
    "baodongkhoi_category": _extract_baodongkhoi_category,
    "baodongnai_category": _extract_baodongnai_category,
    "baodongthap_category": _extract_baodongthap_category,
    "baodautu_category": _extract_baodautu_category,
    "mst_category": _extract_mst_category,
    "baophapluat_category": _extract_baophapluat_category,
    "baoxaydung_category": _extract_baoxaydung_category,
    "giadinh_suckhoedoisong_category": _extract_giadinh_suckhoedoisong_category,
    "soha_category": _extract_soha_category,
    "vtv_category": _extract_vtv_category,
    "vtvgov_category": _extract_vtvgov_category,
    "twentyfourh_category": _extract_twentyfourh_category,
    "vietnamnet_category": _extract_vietnamnet_category,
    "dantri_category": _extract_dantri_category,
    "znews_category": _extract_znews_category,
    "baobinhduong_category": _extract_baobinhduong_category,
    "baobacninhtv_category": _extract_baobacninhtv_category,
    "baotayninh_category": _extract_baotayninh_category,
    "baodaklak_category": _extract_baodaklak_category,
    "baodienbienphu_category": _extract_baodienbienphu_category,
    "baotuyenquang_category": _extract_baotuyenquang_category,
    "baothainguyen_category": _extract_baothainguyen_category,
    "baosonla_category": _extract_baosonla_category,
    "bocongan_category": _extract_bocongan_category,
    "cand_category": _extract_cand_category,
    "baoquangninh_category": _extract_baoquangninh_category,
    "baoquangngai_category": _extract_baoquangngai_category,
    "baoquangtri_category": _extract_baoquangtri_category,
    "baokhanhhoa_category": _extract_baokhanhhoa_category,
    "bvhttdl_category": _extract_bvhttdl_category,
    "breadcrumb_category": _extract_breadcrumb_category,
    "eva_category": _extract_eva_category,
    "baoninhbinh_category": _extract_baoninhbinh_category,
    "tapchitoaan_category": _extract_tapchitoaan_category,
    "khoahocphattrien_category": _extract_khoahocphattrien_category,
    "mofa_category": _extract_mofa_category,
    "moit_category": _extract_mofa_category,
    "qdnd_category": _extract_qdnd_category,
}

_TAG_EXTRACTORS: dict[str, Callable[[BeautifulSoup], List[str]]] = {
    "kenh14_tags": _extract_kenh14_tags,
    "vneconomy_tags": _extract_vneconomy_tags,
    "vietnamnet_tags": _extract_vietnamnet_tags,
    "baodaklak_tags": _extract_baodaklak_tags,
}


def _slug_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or ""
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return None
    slug = parts[-1]
    if slug.endswith(".html"):
        slug = slug[:-5]
    elif slug.endswith(".htm"):
        slug = slug[:-4]
    elif slug.endswith(".chn"):
        slug = slug[:-4]
    return slug.lower() if slug else None


def _prettify_slug(slug: str) -> str:
    tokens = [token for token in re.split(r"[-_]+", slug) if token]
    if not tokens:
        return slug
    return " ".join(tokens).upper()
