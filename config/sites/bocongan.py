from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("bocongan")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://bocongan.gov.vn (Cổng Thông tin điện tử Bộ Công an).

    - Category chính có path dạng /chuyen-muc/<slug>.
    - Bài viết chi tiết có URL dạng /bai-viet/<slug>-<id>.
    - Sapo/description nằm trong đoạn văn có class text-bca-gray-700.
    """

    return SiteConfig(
        key="bocongan",
        base_url="https://bocongan.gov.vn",
        home_path="/",
        category_path_pattern="/chuyen-muc/{slug}",
        article_name="bocongan",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chuyen-muc",
        ),
        deny_category_prefixes=(
            "/gioi-thieu",
            "/albums",
            "/videos",
            "/podcast",
            "/longform",
            "/e-magazine",
            "/infographic",
            "/hoi-dap",
            "/truyen-thong",
            "/chinh-sach-phap-luat",
            "/interpol",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_path_regexes=(
            r"^/bai-viet/.+-\d+/?$",
        ),
        article_link_selector="a[href^='/bai-viet/']",
        description_selectors=(
            "p.text-justify.mb-\\[22px\\].text-bca-gray-700.font-medium.lg\\:text-\\[20px\\]",
            "p.text-justify.text-bca-gray-700.font-medium",
            "p.text-bca-gray-700",
        ),
    )

