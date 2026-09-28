from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vtcnews")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://vtcnews.vn.

    - Bài viết chi tiết có URL dạng \"...-ar<id>.html\".
    - Trang \"Tin mới hôm nay\" liệt kê các bài mới nhất toàn site.
    """

    return _default_site_config(
        "vtcnews",
        "https://vtcnews.vn",
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        # Danh sách bài viết sử dụng link có \"-ar<id>.html\".
        article_link_selector="a[href*='-ar'][href$='.html']",
    )

