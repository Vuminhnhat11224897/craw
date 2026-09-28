from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vietnamnet")
def build_config() -> SiteConfig:
    return _default_site_config("vietnamnet", "https://vietnamnet.vn")

