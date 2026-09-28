from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baolangson")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baolangson.vn (Báo Lạng Sơn điện tử).

    - Category thường có dạng /chinh-tri, /kinh-te, /xa-hoi, ...
    - Bài viết chi tiết có URL đuôi ".html" và kết thúc bằng "-<id>.html".
    """

    return SiteConfig(
        key="baolangson",
        base_url="https://baolangson.vn",
        home_path="/",
        article_name="baolangson",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/phap-luat",
            "/giao-duc",
            "/van-hoa",
            "/the-thao",
            "/giai-tri",
            "/du-lich",
            "/quoc-te",
            "/nong-nghiep",
            "/cong-nghe",
            "/khoa-hoc-tin-hoc",
            "/tieu-diem",
        ),
        deny_category_prefixes=(
            "/multimedia",
            "/video",
            "/media",
            "/rss",
            "/search",
            "/tags",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-\d+\.html$",),
        article_link_selector="article a[href], h3 a[href], h2 a[href], .card-title a[href]",
    )
