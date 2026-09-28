from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baoquangngai")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baoquangngai.vn (Báo Quảng Ngãi điện tử).

    - Category chính có path dạng /chinh-tri, /thoi-su, /kinh-te, ...
    - Bài viết có URL đuôi ".htm" với slug kết thúc bằng "-<id>.htm".
    - Trang category liệt kê bài trong các thẻ article.
    """

    return SiteConfig(
        key="baoquangngai",
        base_url="https://baoquangngai.vn",
        home_path="/",
        article_name="baoquangngai",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/thoi-su",
            "/kinh-te",
            "/xa-hoi",
            "/du-lich",
            "/doi-song",
            "/van-hoa-nghe-thuat",
            "/the-thao",
            "/khoa-hoc-cong-nghe",
            "/phap-luat",
            "/quoc-te",
            "/phong-su",
            "/phong-van-doi-thoai",
            "/quang-ngai-que-minh",
            "/nhin-ra-tinh-ban",
            "/hoat-dong-cua-lanh-dao-tinh",
            "/chuyen-de-chuyen-sau",
            "/thong-tin-can-biet",
        ),
        deny_category_prefixes=(
            "/multimedia",
            "/bao-in",
            "/tin-moi-nhat",
            "/tet-online",
            "/o-to-xe-may",
            "/ban-do-quang-ngai",
            "/@baoquangngai.vn",
        ),
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(r"-\d+\.htm$",),
        deny_article_prefixes=(
            "/bao-in",
            "/event",
            "/expert",
            "/multimedia",
            "/tin-moi-nhat",
            "/tet-online",
            "/o-to-xe-may",
            "/ban-do-quang-ngai",
        ),
        article_link_selector="article a[href$='.htm']",
        description_selectors=(
            "p.sapo",
            "#body .sapo",
        ),
    )

