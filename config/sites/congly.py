from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("congly")
def build_config() -> SiteConfig:
    return _default_site_config("congly", "https://congly.vn")

