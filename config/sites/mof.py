from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("mof")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://www.mof.gov.vn (Cổng thông tin Bộ Tài chính).

    - Trang sử dụng SPA, danh sách bài lấy qua API nội bộ.
    - URL bài viết dùng pattern /{rootSlug}/{categorySlug}/{articleSlug}.
    """

    return SiteConfig(
        key="mof",
        base_url="https://www.mof.gov.vn",
        home_path="/",
        article_name="mof",
        max_categories=1,
        max_articles_per_category=80,
        allowed_locales=("vi", "vi-vn"),
    )

