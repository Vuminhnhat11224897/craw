from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodanang")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://baodanang.vn.

    - Category chính có path dạng /chinh-tri, /xa-hoi, /kinh-te, ...
    - Bài viết thường có URL đuôi .html (không nằm trong thư mục category).
    - Danh sách bài trong category dùng thẻ h3.b-grid__title > a.
    """

    return SiteConfig(
        key="baodanang",
        base_url="https://baodanang.vn",
        home_path="/",
        article_name="baodanang",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/xa-hoi",
            "/kinh-te",
            "/nong-nghiep-nong-thon",
            "/quoc-phong-an-ninh",
            "/the-gioi",
            "/the-thao",
            "/van-hoa-van-nghe",
            "/doi-song",
            "/du-lich",
            "/khoa-hoc-cong-nghe",
            "/su-kien-binh-luan",
            "/co-hoi-dau-tu",
            "/theo-buoc-chan-nguoi-quang",
            "/toa-soan-ban-doc",
            "/tin-moi-nhat",
        ),
        deny_category_prefixes=(
            "/media",
            "/podcast",
            "/truyen-hinh",
            "/quang-cao-rao-vat",
            "/am-duong-lich-hom-nay",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        article_link_selector="h3.b-grid__title a[href]",
    )

