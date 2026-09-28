from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("kenh14")
def build_config() -> SiteConfig:
    return _default_site_config("kenh14", "https://kenh14.vn")

