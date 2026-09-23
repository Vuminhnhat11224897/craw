from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("eva")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://eva.vn (EVA).

    - Category thường có hậu tố dạng "-c123.html", nên giữ nguyên path
      tìm được từ trang chủ để tránh canonicalize sai.
    - Bài viết thường có đuôi .html.
    """

    return SiteConfig(
        key="eva",
        base_url="https://eva.vn",
        home_path="/",
        canonicalize_category_paths=False,
        article_name="eva",
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html", ".htm"),
    )
