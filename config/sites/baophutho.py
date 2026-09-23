from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baophutho")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baophutho.vn (Báo Phú Thọ điện tử).

    - Category dạng /{slug}.
    - Bài viết có dạng /{slug}-{id}.htm.
    """

    return SiteConfig(
        key="baophutho",
        base_url="https://baophutho.vn",
        home_path="/",
        article_name="baophutho",
        category_path_pattern="/{slug}",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/phu-tho-24h",
            "/phong-vi-dat-to",
            "/den-hung",
            "/du-lich-le-hoi",
            "/chinh-tri",
            "/xay-dung-dang",
            "/quoc-hoi-hoi-dong-nhan-dan",
            "/hoc-va-lam-theo-bac",
            "/van-hoa-xa-hoi",
            "/xa-hoi",
            "/van-hoc-nghe-thuat",
            "/van-hoa",
            "/dan-toc-ton-giao",
            "/net-dep-doi-thuong",
            "/kinh-te",
            "/gia-ca-thi-truong",
            "/giao-duc",
            "/y-te",
            "/phong-su-ghi-chep",
            "/quoc-te",
            "/quoc-phong-an-ninh",
            "/giai-tri",
            "/the-thao",
            "/toa-soan-ban-doc",
            "/cong-dong",
            "/ong-kinh-phong-vien",
            "/khoa-hoc-cong-nghe",
            "/chuyen-doi-so",
            "/o-to-xe-may",
            "/tin24h",
        ),
        deny_category_prefixes=(
            "/video",
            "/podcast",
            "/emagazine",
            "/topic",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(r"/[^/]+-\d+\.htm$",),
        deny_article_prefixes=(
            "/video",
            "/podcast",
            "/emagazine",
        ),
        article_link_selector="a[href$='.htm']",
    )
