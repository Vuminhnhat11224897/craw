from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("hanoimoi")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://hanoimoi.vn.

    - Category có path dạng /chinh-tri, /kinh-te, /do-thi, ...
    - Bài viết chi tiết có URL dạng "slug-<id>.html".
    - Loại bỏ các trang event tổng hợp (đuôi -event<id>.html).
    """

    return SiteConfig(
        key="hanoimoi",
        base_url="https://hanoimoi.vn",
        home_path="/",
        article_name="hanoimoi",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/kinh-te",
            "/do-thi",
            "/van-hoa",
            "/xa-hoi",
            "/giao-duc",
            "/y-te",
            "/the-gioi",
            "/du-lich",
            "/nong-nghiep-nong-thon",
            "/khoa-hoc-cong-nghe",
            "/doi-song",
        ),
        deny_category_prefixes=(
            "/an-pham",
            "/tin-moi-nhat",
            "/ban-do-ha-noi",
            "/multimedia",
            "/video",
            "/emagazine",
            "/infographic",
            "/photo",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(
            r"/(?!.*-event\d+\.html$).+-\d+\.html$",
        ),
        article_link_selector="h3 a[href]",
        description_selectors=(
            "meta[name='description']",
            "meta[property='og:description']",
        ),
    )

