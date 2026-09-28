from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baohungyen")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baohungyen.vn (Báo Hưng Yên điện tử).

    - Category dạng /{slug} (menu chính có cả dạng chữ hoa và thường).
    - Bài viết có URL dạng "...-<id>.html".
    """

    return SiteConfig(
        key="baohungyen",
        base_url="https://baohungyen.vn",
        home_path="/",
        category_path_pattern="/{slug}",
        article_name="baohungyen",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/Chinh-tri",
            "/kinh-te",
            "/Kinh-te",
            "/xa-hoi",
            "/Xa-hoi",
            "/van-hoa",
            "/Van-hoa",
            "/the-thao",
            "/The-thao",
            "/an-ninh-quoc-phong",
            "/quoc-te",
            "/giao-duc",
            "/Giao-duc",
            "/dat-va-nguoi-hung-yen",
            "/ban-doc",
            "/Ban-doc",
            "/doi-song",
            "/phap-luat-doi-song",
            "/bien-dao-Viet-Nam",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-\d+\.html$",),
    )

