from __future__ import annotations

from typing import Callable, Dict

from .base import SiteConfig

SiteConfigBuilder = Callable[[], SiteConfig]
SITE_CONFIG_BUILDERS: Dict[str, SiteConfigBuilder] = {}


def register_site(key: str) -> Callable[[SiteConfigBuilder], SiteConfigBuilder]:
    """Decorator đăng ký site config builder theo key."""

    def decorator(func: SiteConfigBuilder) -> SiteConfigBuilder:
        if key in SITE_CONFIG_BUILDERS:
            raise KeyError(f"Duplicate site key registration: {key}")
        SITE_CONFIG_BUILDERS[key] = func
        return func

    return decorator
