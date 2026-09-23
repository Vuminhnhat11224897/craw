from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodongkhoi")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baodongkhoi.vn.

    Trang baodongkhoi.vn render nội dung với base href trỏ về
    dongkhoi.baovinhlong.vn, nên dùng host này để thu thập link bài viết.
    """

    return SiteConfig(
        key="baodongkhoi",
        base_url="https://dongkhoi.baovinhlong.vn",
        home_path="/",
        article_name="baodongkhoi",
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
        deny_article_prefixes=(
            "/https/",
        ),
    )

