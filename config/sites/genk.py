from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("genk")
def build_config() -> SiteConfig:
    return _default_site_config("genk", "https://genk.vn")

