from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baokhanhhoa")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baokhanhhoa.vn.

    - Category dạng /{slug}/.
    - Bài viết có URL dạng /{category}/YYYYMM/{slug}-{id}/ (id hex 7 ký tự).
    """

    return SiteConfig(
        key="baokhanhhoa",
        base_url="https://baokhanhhoa.vn",
        home_path="/",
        article_name="baokhanhhoa",
        category_path_pattern="/{slug}/",
        max_categories=40,
        max_articles_per_category=80,
        deny_exact_paths=(
            "/",
        ),
        deny_category_prefixes=(
            "/video",
            "/podcast",
            "/multimedia",
        ),
        deny_article_prefixes=(
            "/video",
            "/podcast",
            "/multimedia",
        ),
        allowed_article_path_regexes=(
            r"^/[^/]+/\d{6}/[^/]+-[0-9a-f]{7}/?$",
        ),
        article_link_selector="div.item a[href]",
        allowed_locales=("vi", "vi-vn"),
    )
