from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("mae")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://mae.gov.vn (Bộ Nông nghiệp và Môi trường).

    - Category list page dạng /chuyen-muc/<slug>.htm.
    - Bài viết dạng /<slug>-<id>.htm hoặc /tin-*/<slug>-<id>.htm.
    """

    return SiteConfig(
        key="mae",
        base_url="https://mae.gov.vn",
        home_path="/",
        category_path_pattern="/chuyen-muc/{slug}.htm",
        article_name="mae",
        max_categories=30,
        max_articles_per_category=80,
        delay_seconds=1.5,
        allow_category_prefixes=(
            "/chuyen-muc/",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"^/[^/]+-\\d+\\.htm$",
            r"^/(?:tin-[^/]+|tin-tuc--su-kien)/[^/]+-\\d+\\.htm$",
        ),
        deny_article_prefixes=(
            "/chuyen-muc",
            "/gioi-thieu",
            "/Pages",
            "/lien-ket",
            "/van-ban",
        ),
        article_link_selector="a.item-tintuc[href]",
        blocked_content_markers=(
            "Thông báo từ chối truy cập",
            "Hệ thống đang gặp vấn đề khi xử lý yêu cầu của bạn",
        ),
        timeout_seconds=30,
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        },
    )

