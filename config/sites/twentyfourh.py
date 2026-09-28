from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("24h")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://www.24h.com.vn.

    - Category có path dạng /bong-da-c48.html, /kinh-doanh-c161.html, ...
    - Bài viết chi tiết có sapo trong h2#article_sapo và nội dung chính
      trong <article id="article_body" ...>.
    """

    return SiteConfig(
        key="24h",
        base_url="https://www.24h.com.vn",
        home_path="/",
        article_name="24h",
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        description_selectors=(
            "h2#article_sapo",
            "h2.cate-24h-foot-arti-deta-sum",
        ),
    )

