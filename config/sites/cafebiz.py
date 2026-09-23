from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("cafebiz")
def build_config() -> SiteConfig:
    return _default_site_config(
        "cafebiz",
        "https://cafebiz.vn",
        allowed_locales=("vi", "vi-vn"),
        allowed_article_host_suffixes=(".vn",),
        description_selectors=(
            "h2.sapo",
            "p.sapo",
            "div.sapo",
        ),
    )

