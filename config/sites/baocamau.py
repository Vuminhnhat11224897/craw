from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baocamau")
def build_config() -> SiteConfig:
    return _default_site_config(
        "baocamau",
        "https://baocamau.vn",
        allowed_article_url_suffixes=(".html",),
    )

