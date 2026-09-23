from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("mard")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://www.mard.gov.vn (Cổng thông tin điện tử Bộ NN&PTNT).

    - Trang chủ dùng /Pages/default.aspx.
    - Category list page dạng /Pages/tin-*.aspx và /Pages/danh-sach-tin-*.aspx.
    - Bài viết chi tiết dạng /Pages/<slug>.aspx (loại trừ các list page).
    """

    return SiteConfig(
        key="mard",
        base_url="https://mard.gov.vn",
        home_path="/Pages/default.aspx",
        category_path_pattern="/Pages/{slug}.aspx",
        article_name="mard",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/Pages/tin-",
            "/Pages/danh-sach-tin-",
        ),
        deny_category_prefixes=(
            "/Pages/danh-sach-tin-video.aspx",
        ),
        deny_exact_paths=(
            "/",
            "/Pages/default.aspx",
        ),
        allowed_article_url_suffixes=(".aspx",),
        allowed_article_path_regexes=(
            r"^/Pages/.+\\.aspx$",
        ),
        deny_article_prefixes=(
            "/Pages/tin-",
            "/Pages/danh-sach-tin-",
            "/Pages/default.aspx",
        ),
        article_link_selector="a[href^='/Pages/'][href*='.aspx']",
        timeout_seconds=40,
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        },
    )

