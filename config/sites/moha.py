from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("moha")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://moha.gov.vn (Bộ Nội vụ).

    - Category có path dạng /chuyen-muc/<slug>---id<id>.
    - Bài viết có path dạng /tin-tuc/<slug>---id<id>.
    """

    return SiteConfig(
        key="moha",
        base_url="https://moha.gov.vn",
        home_path="/",
        category_path_pattern="/chuyen-muc/{slug}",
        article_name="moha",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chuyen-muc",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_path_regexes=(
            r"^/tin-tuc/.+---id\d+/?$",
        ),
        article_link_selector="a[href*='/tin-tuc/']",
    )

