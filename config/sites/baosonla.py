from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baosonla")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baosonla.vn (Báo Sơn La điện tử).

    - Category chủ yếu có dạng /{slug}.html theo menu chính.
    - Bài viết có dạng /{category}/{slug}-{id}.html.
    - Sapo/description ưu tiên lấy từ meta description.
    - Link bài viết thường dùng class "cms-link".
    """

    return SiteConfig(
        key="baosonla",
        base_url="https://baosonla.vn",
        home_path="/",
        category_path_pattern="/{slug}.html",
        article_name="baosonla",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su-chinh-tri",
            "/xay-dung-dang",
            "/bao-ve-nen-tang-tu-tuong-cua-dang",
            "/phong-chong-tham-nhung",
            "/kinh-te",
            "/nong-nghiep",
            "/cong-nghiep-ttcn",
            "/thuong-mai-dich-vu",
            "/van-hoa-xa-hoi",
            "/xa-hoi",
            "/khoa-giao",
            "/suc-khoe",
            "/an-toan-giao-thong",
            "/the-thao",
            "/ban-can-biet",
            "/quoc-phong-an-ninh",
            "/quoc-phong",
            "/an-ninh-trat-tu",
            "/doi-ngoai",
            "/quoc-te",
            "/du-lich",
            "/nong-thon-moi",
            "/dien-dan-cu-tri",
            "/phong-su",
            "/phap-luat",
            "/cai-cach-hanh-chinh",
        ),
        deny_category_prefixes=(
            "/emagazine",
            "/thong-tin-quang-cao",
            "/bao-in",
            "/trang-dia-phuong",
            "/lien-he",
            "/video",
        ),
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"^/[^/]+/.+\.html$",),
        deny_article_prefixes=(
            "/emagazine",
            "/thong-tin-quang-cao",
            "/video",
        ),
        article_link_selector="a.cms-link[href$='.html']",
        description_selectors=(
            "meta[name='description']",
            "meta[property='og:description']",
        ),
    )

