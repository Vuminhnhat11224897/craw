from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baocantho")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baocantho.com.vn.

    - Category dạng /{slug}/, có thể có subcategory.
    - Bài viết dùng đuôi .html với slug "-a<id>.html".
    """

    return SiteConfig(
        key="baocantho",
        base_url="https://baocantho.com.vn",
        home_path="/",
        article_name="baocantho",
        category_path_pattern="/{slug}/",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi-phap-luat",
            "/quoc-phong-an-ninh",
            "/the-gioi",
            "/giao-duc",
            "/y-te",
            "/cong-nghe",
            "/chuyen-doi-so",
            "/van-hoa-giai-tri",
            "/the-thao",
            "/du-lich",
        ),
        deny_category_prefixes=(
            "/video",
            "/xem-bao",
            "/news",
            "/khmer",
            "/bang-gia-quang-cao-bao-in",
            "/tim-kiem",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-a\d+\.html$",),
    )

