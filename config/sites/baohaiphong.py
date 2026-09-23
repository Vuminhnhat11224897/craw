from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baohaiphong")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://baohaiphong.vn.

    - Category chính có path dạng /chinh-tri, /kinh-te, /xa-hoi, ...
    - Bài viết chi tiết có URL đuôi .html (slug-id.html).
    - Danh sách bài trong category thường dùng thẻ h3 > a.
    """

    return SiteConfig(
        key="baohaiphong",
        base_url="https://baohaiphong.vn",
        home_path="/",
        article_name="baohaiphong",
        max_categories=40,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/goc-nhin",
            "/khoa-hoc-giao-duc",
            "/phap-luat",
            "/bat-dong-san",
            "/van-hoa-giai-tri",
            "/van-nghe",
            "/quoc-te",
            "/the-thao",
            "/doi-song",
            "/dat-va-nguoi-xu-dong",
            "/ban-doc",
            "/du-lich",
            "/su-kien-qua-anh",
            "/xe",
        ),
        deny_category_prefixes=(
            "/video",
            "/emagazine",
            "/podcast",
            "/infographic",
            "/thong-tin-quang-cao",
            "/an-pham",
            "/thoi-tiet-hai-phong",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        deny_article_prefixes=(
            "/an-pham",
            "/video",
            "/podcast",
            "/emagazine",
            "/infographic",
            "/thong-tin-quang-cao",
        ),
        article_link_selector="h3 a[href]",
        description_selectors=(
            "p.sc-longform-header-sapo",
            "p.block-sc-sapo",
            ".sc-longform-header-sapo",
        ),
    )

