from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baoninhbinh")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baoninhbinh.org.vn (Báo Ninh Bình điện tử).

    - Category dạng /{slug} (không trailing slash).
    - Bài viết có URL dạng "...-<15 digits>.html".
    - E-newspaper nằm ở /bao-in và /doc-bao-in (loại trừ khỏi crawl báo điện tử).
    """

    return SiteConfig(
        key="baoninhbinh",
        base_url="https://baoninhbinh.org.vn",
        home_path="/",
        category_path_pattern="/{slug}",
        article_name="baoninhbinh",
        max_categories=40,
        max_articles_per_category=80,
        deny_exact_paths=(
            "/",
        ),
        deny_category_prefixes=(
            "/bao-in",
            "/doc-bao-in",
            "/da-phuong-tien-multimedia",
            "/video",
            "/podcast",
            "/dang-nhap",
        ),
        deny_article_prefixes=(
            "/bao-in",
            "/doc-bao-in",
            "/da-phuong-tien-multimedia",
            "/video",
            "/podcast",
            "/dang-nhap",
        ),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-\d{15}\.html$",),
        article_link_selector="a[href$='.html']",
        allowed_locales=("vi", "vi-vn"),
    )
