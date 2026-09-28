from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodautu")
def build_config() -> SiteConfig:
    return _default_site_config("baodautu", "https://baodautu.vn")

