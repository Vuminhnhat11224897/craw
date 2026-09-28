from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("nguoiquansat")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="nguoiquansat",
        base_url="https://nguoiquansat.vn",
        home_path="/",
        article_name="nguoiquansat",
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-\d+\.html$",),
        article_link_selector="a[href$='.html']",
    )
