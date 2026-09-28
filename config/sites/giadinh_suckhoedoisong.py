from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("giadinh_suckhoedoisong")
def build_config() -> SiteConfig:
    return _default_site_config(
        "giadinh_suckhoedoisong",
        "https://giadinh.suckhoedoisong.vn",
        category_path_pattern="/{slug}.htm",
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(r"-\d+\.htm$",),
        article_link_selector="a[href$='.htm']",
    )
