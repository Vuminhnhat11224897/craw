from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("nongnghiepmoitruong")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="nongnghiepmoitruong",
        base_url="https://nongnghiepmoitruong.vn",
        home_path="/",
        article_name="nongnghiepmoitruong",
        deny_exact_paths=("/",),
        description_selectors=(
            "h2.main-intro.detail-intro",
        ),
    )

