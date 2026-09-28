from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("moj")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://www.moj.gov.vn (Bộ Tư pháp).

    - Category dạng /qt/tintuc/Pages/<slug>.aspx.
    - Bài viết chi tiết dùng query param ItemID.
    """

    return SiteConfig(
        key="moj",
        base_url="https://www.moj.gov.vn",
        home_path="/Pages/home.aspx",
        category_path_pattern="/qt/tintuc/Pages/{slug}.aspx",
        article_name="moj",
        max_categories=200,
        max_articles_per_category=80,
        deny_category_prefixes=(
            "/UserControls",
        ),
        deny_exact_paths=(
            "/",
            "/Pages/home.aspx",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".aspx",),
        allowed_article_path_regexes=(
            r"^/qt/tintuc/Pages/.+\\.aspx$",
        ),
        article_link_selector="a[href*='ItemID=']",
        keep_query_params=True,
    )

