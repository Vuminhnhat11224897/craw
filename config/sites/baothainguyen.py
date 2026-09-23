from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baothainguyen")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baothainguyen.vn (Báo Thái Nguyên điện tử).

    - Category dạng /{slug}/ trên menu chính.
    - Bài viết có URL dạng /{category}/{YYYYMM}/{slug}-{id}/.
    - Link bài viết trong trang category dùng class "title2".
    """

    return SiteConfig(
        key="baothainguyen",
        base_url="https://baothainguyen.vn",
        home_path="/",
        article_name="baothainguyen",
        category_path_pattern="/{slug}/",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su-thai-nguyen",
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/phap-luat",
            "/giao-duc",
            "/y-te",
            "/van-hoa",
            "/van-nghe-thai-nguyen",
            "/the-thao",
            "/giao-thong",
            "/o-to-xe-may",
            "/tai-nguyen-moi-truong",
            "/quoc-phong-an-ninh",
            "/quoc-te",
            "/que-huong-dat-nuoc",
            "/ban-doc",
            "/tieu-diem",
            "/tin-moi",
            "/thong-tin-can-biet",
        ),
        deny_category_prefixes=(
            "/audio",
            "/audio-bao-thai-nguyen",
            "/audio-thai-nguyen",
            "/multimedia",
            "/podcast",
            "/video",
            "/doc-bao-in",
            "/tim-kiem",
            "/thong-tin-quang-cao",
        ),
        deny_exact_paths=("/",),
        allowed_article_path_regexes=(
            r"/\d{6}/[^/]+/?$",
        ),
        deny_article_prefixes=(
            "/audio",
            "/audio-bao-thai-nguyen",
            "/audio-thai-nguyen",
            "/multimedia",
            "/podcast",
            "/video",
            "/doc-bao-in",
        ),
        article_link_selector="a.title2[href]",
        description_selectors=("div.desc",),
    )

