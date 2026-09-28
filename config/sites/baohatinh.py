from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baohatinh")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baohatinh.vn (Báo Hà Tĩnh).

    - Category dạng /{slug}/ (có subcategory).
    - Bài viết có URL dạng "...-post<id>.html".
    - Link bài viết dùng class "cms-link".
    """

    return SiteConfig(
        key="baohatinh",
        base_url="https://baohatinh.vn",
        home_path="/",
        category_path_pattern="/{slug}/",
        article_name="baohatinh",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri/",
            "/kinh-te/",
            "/xa-hoi/",
            "/van-hoa-giai-tri/",
            "/phap-luat/",
            "/the-thao/",
            "/the-gioi/",
            "/ve-ha-tinh/",
            "/doi-song/",
            "/cong-nghe/",
            "/cong-dong/",
            "/xe/",
        ),
        deny_category_prefixes=(
            "/epaper/",
            "/multimedia/",
            "/short-video/",
            "/podcast/",
            "/video/",
            "/emagazine/",
        ),
        deny_exact_paths=(
            "/",
            "/tin-moi.html",
        ),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-post\d+\.html$",),
        article_link_selector="a.cms-link[href]",
        allowed_locales=("vi", "vi-vn"),
    )

