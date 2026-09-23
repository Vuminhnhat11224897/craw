from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baoquangninh")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baoquangninh.vn (Báo Quảng Ninh điện tử).

    - Category dạng /{slug} và có các chuyên mục chính trên menu.
    - Bài viết có URL kết thúc bằng "-<id>.html".
    """

    return SiteConfig(
        key="baoquangninh",
        base_url="https://baoquangninh.vn",
        home_path="/",
        article_name="baoquangninh",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/phap-luat",
            "/the-thao",
            "/du-lich",
            "/van-hoa",
            "/quoc-te",
            "/doi-song",
            "/khoa-hoc-cong-nghe",
            "/ban-doc",
            "/multimedia",
            "/truyen-hinh",
            "/phat-thanh",
        ),
        deny_category_prefixes=(
            "/intro",
            "/users",
            "/thong-tin-quang-cao",
        ),
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-\d+\.html$",),
        article_link_selector="article.card a[href], .card-content a[href]",
    )

