from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baoxaydung")
def build_config() -> SiteConfig:
    return _default_site_config(
        "baoxaydung",
        "https://baoxaydung.vn",
        # Bài viết thường có đuôi "-<id>.htm"; dùng regex để bỏ qua link chuyên mục.
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"/.+-\d+\.htm$",
        ),
    )

