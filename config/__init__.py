from __future__ import annotations

"""Cấu hình nguồn cho API realtime và worker ảnh."""

from typing import Dict

from .base import SiteConfig
from .registry import SITE_CONFIG_BUILDERS
from .sites import load_site_modules


def get_supported_sites() -> Dict[str, SiteConfig]:
    """Trả về dict {site_key: SiteConfig} cho tất cả các trang được hỗ trợ."""
    load_site_modules()
    return {
        key: SITE_CONFIG_BUILDERS[key]() for key in sorted(SITE_CONFIG_BUILDERS)
    }
