from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vtvgov")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://vtv.gov.vn.

    Tách key riêng để tránh nhầm với site https://vtv.vn.
    """

    return SiteConfig(
        key="vtvgov",
        base_url="https://vtv.gov.vn",
        home_path="/",
        category_path_pattern="/{slug}.htm",
        canonicalize_category_paths=False,
        article_name="vtv",
        max_categories=30,
        max_articles_per_category=80,
        # Cho phép "/" được coi như 1 category để crawl trực tiếp link bài
        # ngay trên trang chủ (vtv.gov.vn hiển thị nhiều link /news/* ở homepage).
        deny_exact_paths=(),
        deny_category_prefixes=(
            "/lien-he",
            "/gioi-thieu",
            "/dieu-khoan",
            "/login",
            "/danh-ba",
            "/thu-dien-tu",
            "/dang-ky",
            "/video",
            "/podcast",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_internal_host_suffixes=(
            "vtv.gov.vn",
            "vtv.vn",
        ),
        category_fetch_fallback_strip_suffixes=(
            ".htm",
            ".html",
        ),
        allowed_article_host_suffixes=(
            "vtv.gov.vn",
            "vtv.vn",
        ),
        # Link bài viết trên vtv.gov.vn thường không có đuôi .html/.htm
        # (ví dụ: https://vtv.gov.vn/news/tin-tuc-su-kien/<slug>), nên không lọc theo suffix.
        allowed_article_url_suffixes=(),
        allowed_article_path_regexes=(
            r"^/news/",
        ),
    )

