from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("mst")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://mst.gov.vn (Cổng thông tin điện tử Bộ Khoa học và Công nghệ).

    - Category dạng /tin-tuc-su-kien[/<slug>].htm.
    - Bài viết chi tiết thường kết thúc bằng "-<digits>.htm".
    """

    return SiteConfig(
        key="mst",
        base_url="https://mst.gov.vn",
        home_path="/",
        category_path_pattern="/{slug}.htm",
        article_name="mst",
        max_categories=30,
        max_articles_per_category=80,
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"^/.+-\d{8,}\.htm$",
        ),
        article_link_selector="div.box-category-item a[href]",
        description_selectors=(
            "div.detail-sapo",
            "meta[name='description']",
            "meta[property='og:description']",
        ),
    )

