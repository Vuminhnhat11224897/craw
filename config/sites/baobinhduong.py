from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baobinhduong")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baobinhduong.vn.

    - Category chính có path dạng /chinh-tri, /kinh-te, ...
    - Bài viết có URL đuôi .html với slug "-a<id>.html".
    - Danh sách bài trong category dùng block .article-item và tiêu đề h3 > a.
    """

    return SiteConfig(
        key="baobinhduong",
        base_url="https://baobinhduong.vn",
        home_path="/",
        article_name="baobinhduong",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/the-thao",
            "/giao-duc",
            "/phap-luat",
            "/y-te",
            "/nhip-song-so",
            "/phan-tich",
            "/ban-doc",
            "/du-lich",
            "/quoc-te",
            "/toi-yeu-binh-duong",
        ),
        deny_category_prefixes=(
            "/video",
            "/podcast",
            "/infographic",
            "/longform",
            "/xem-albumphoto",
            "/xem-bao",
            "/en",
            "/cn",
            "/tim-kiem",
            "/su-kien",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-a\d+\.html$",),
        article_link_selector=".article-item a[href], h3 a[href], h2 a[href]",
    )

