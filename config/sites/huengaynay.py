from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("huengaynay")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://huengaynay.vn.

    Chưa có rule đặc thù (selector/category prefix) do môi trường chạy không truy
    cập được mạng để kiểm tra cấu trúc HTML hiện tại; dùng heuristic chung và
    loại bỏ một số prefix không phải chuyên mục/bài viết.
    """

    return SiteConfig(
        key="huengaynay",
        base_url="https://huengaynay.vn",
        home_path="/",
        canonicalize_category_paths=False,
        article_name="huengaynay",
        max_categories=30,
        max_articles_per_category=80,
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".htm", ".html"),
        deny_category_prefixes=(
            "/rss",
            "/feed",
            "/video",
            "/podcast",
            "/multimedia",
            "/media",
            "/lien-he",
            "/gioi-thieu",
            "/dang-nhap",
            "/login",
            "/search",
            "/tim-kiem",
            "/tag",
            "/tags",
        ),
        deny_article_prefixes=(
            "/rss",
            "/feed",
            "/video",
            "/podcast",
            "/multimedia",
            "/media",
            "/lien-he",
            "/gioi-thieu",
            "/dang-nhap",
            "/login",
            "/search",
            "/tim-kiem",
            "/tag",
            "/tags",
        ),
    )

