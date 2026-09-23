from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodongthap")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baodongthap.vn (Báo Đồng Tháp Online).

    - Category dạng /{slug}/.
    - Bài viết có đuôi ".html" với slug kết thúc "-a<id>.html".
    """

    return SiteConfig(
        key="baodongthap",
        base_url="https://baodongthap.vn",
        home_path="/",
        article_name="baodongthap",
        category_path_pattern="/{slug}/",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/van-hoa-nghe-thuat",
            "/the-thao",
            "/giao-duc",
            "/phap-luat",
            "/suc-khoe-y-te",
            "/quoc-te",
            "/khoa-hoc",
        ),
        deny_category_prefixes=(
            "/video",
            "/podcast",
            "/longform",
            "/infographic",
            "/xem-bao",
            "/xem-albumphoto",
            "/tim-kiem",
            "/en",
            "/files",
        ),
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-a\d+\.html$",),
        deny_article_prefixes=(
            "/en/",
            "/video",
            "/podcast",
            "/longform",
            "/infographic",
            "/xem-albumphoto",
        ),
        article_link_selector="a.news-title[href], a.title[href]",
    )

