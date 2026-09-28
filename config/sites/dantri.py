from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("dantri")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="dantri",
        base_url="https://dantri.com.vn",
        home_path="/",
        article_name="dantri",
        deny_exact_paths=("/",),
        description_selectors=(
            ".singular-sapo",
            ".singular-sapo h2",
            "meta[name='description']",
        ),
    )

