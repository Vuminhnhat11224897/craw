from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("mattran")
def build_config() -> SiteConfig:
    return _default_site_config("mattran", "https://mattran.org.vn")

