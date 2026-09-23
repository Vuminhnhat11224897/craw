from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baoquangtri")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baoquangtri.vn (Báo và phát thanh, truyền hình Quảng Trị).

    - Category dạng /{slug}/, có thể có subcategory.
    - Bài viết thường có URL dạng /{category}/{YYYYMM}/{slug}-{id}/.
    """

    return SiteConfig(
        key="baoquangtri",
        base_url="https://baoquangtri.vn",
        home_path="/",
        article_name="baoquangtri",
        category_path_pattern="/{slug}/",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri/",
            "/dat-va-nguoi-quang-binh/",
            "/dat-va-nguoi-quang-tri/",
            "/du-lich/",
            "/giao-duc/",
            "/khoa-hoc-cong-nghe/",
            "/kinh-te/",
            "/multimedia/",
            "/phap-luat/",
            "/phong-su-ky-su/",
            "/quoc-phong-an-ninh/",
            "/quoc-te/",
            "/suc-khoe/",
            "/the-thao/",
            "/thoi-su/",
            "/toa-soan-ban-doc/",
            "/van-hoa/",
            "/xa-hoi/",
            "/moi-nong/",
        ),
        deny_category_prefixes=(
            "/doc-bao-in/",
            "/thong-tin-quang-cao-tuyen-dung/",
        ),
        deny_exact_paths=("/",),
        allowed_article_path_regexes=(
            r"^/[a-z0-9-]+(?:/[a-z0-9-]+)?/\d{6}/[a-z0-9-]+-[0-9a-f]+/?$",
        ),
        deny_article_prefixes=(
            "/doc-bao-in/",
            "/thong-tin-quang-cao-tuyen-dung/",
        ),
        article_link_selector="a.h2[href], a.h3[href], a.card-img[href]",
    )

