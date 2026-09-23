from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodaklak")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baodaklak.vn (Báo Đắk Lắk điện tử).

    - Category dạng /{slug}/, có thể có subcategory.
    - Bài viết thường có URL dạng /{category}/{YYYYMM}/{slug}/.
    """

    return SiteConfig(
        key="baodaklak",
        base_url="https://baodaklak.vn",
        home_path="/",
        article_name="baodaklak",
        category_path_pattern="/{slug}/",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/giao-duc",
            "/y-te-suc-khoe",
            "/chinh-sach-xa-hoi",
            "/phap-luat",
            "/an-ninh-quoc-phong",
            "/quoc-te",
            "/the-thao",
            "/van-hoa-du-lich-van-hoc-nghe-thuat",
            "/du-lich",
            "/khoa-hoc-cong-nghe",
            "/moi-truong",
            "/trang-tin-dia-phuong",
            "/thong-tin-doanh-nghiep-tu-gioi-thieu",
            "/phong-su-ky-su",
            "/van-de-ban-doc-quan-tam",
        ),
        deny_category_prefixes=(
            "/multimedia",
            "/video",
            "/doc-bao-in",
            "/tim-kiem",
        ),
        deny_exact_paths=("/",),
        allowed_article_path_regexes=(
            r"/\d{6}/[^/]+/?$",
        ),
        deny_article_prefixes=(
            "/multimedia",
            "/video",
            "/doc-bao-in",
            "/tim-kiem",
        ),
        article_link_selector="a.title5[href]",
    )

