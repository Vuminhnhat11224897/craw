from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("vietnamfinance")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://vietnamfinance.vn.

    - Category thường ở dạng /{slug}/ hoặc một số trang tổng hợp .htm.
    - Bài viết có dạng "...-d<id>.html".
    - Loại trừ các chuyên mục multimedia/e-magazine khỏi crawl báo điện tử thường.
    """

    return SiteConfig(
        key="vietnamfinance",
        base_url="https://vietnamfinance.vn",
        home_path="/",
        canonicalize_category_paths=False,
        article_name="vietnamfinance",
        max_categories=40,
        max_articles_per_category=100,
        deny_exact_paths=("/",),
        deny_category_prefixes=(
            "/video",
            "/photo",
            "/infographic",
            "/infographics",
            "/emagazine",
            "/e-magazine",
            "/podcast",
            "/tim-kiem",
            "/dang-nhap",
        ),
        deny_article_prefixes=(
            "/video",
            "/photo",
            "/infographic",
            "/infographics",
            "/emagazine",
            "/e-magazine",
            "/podcast",
            "/tim-kiem",
            "/dang-nhap",
        ),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-d\d+\.html$",),
        article_link_selector="a[href*='-d'][href$='.html']",
        allowed_locales=("vi", "vi-vn"),
    )
