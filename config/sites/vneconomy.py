from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vneconomy")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="vneconomy",
        base_url="https://vneconomy.vn",
        home_path="/",
        article_name="vneconomy",
        deny_exact_paths=("/",),
        description_selectors=(
            "div.news-sapo",
            "[data-field='sapo']",
            "div.news-sapo[data-field='sapo'] p",
            "div.news-sapo p",
            "[data-field='sapo'] p",
            "div.news-sapo[data-field='sapo'] p b",
        ),
    )

