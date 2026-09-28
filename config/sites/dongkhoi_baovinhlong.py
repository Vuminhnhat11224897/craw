from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("dongkhoi_baovinhlong")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://dongkhoi.baovinhlong.vn.

    - Category dạng /{slug}/ (có trailing slash).
    - Bài viết có URL kết thúc bằng "-a<id>.html".
    """

    return SiteConfig(
        key="dongkhoi_baovinhlong",
        base_url="https://dongkhoi.baovinhlong.vn",
        home_path="/",
        article_name="dongkhoi_baovinhlong",
        category_path_pattern="/{slug}/",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/chinh-tri",
            "/kinh-te",
            "/phap-luat",
            "/xa-hoi",
            "/van-hoa",
            "/khoa-giao",
            "/the-thao",
            "/quoc-phong",
            "/an-ninh",
            "/ban-doc",
            "/quoc-te",
        ),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-a\d+\.html$",),
    )

