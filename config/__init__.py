from __future__ import annotations

"""
Khai báo cấu hình cho nhiều trang báo.

Ý tưởng:
- Mỗi trang báo (vnexpress, tuoitre, ...) được mô tả bằng một `SiteConfig`
  gồm base_url, các rule lọc category, số lượng bài tối đa, v.v.
- Phần logic crawl/parse HTML sẽ ở `crawler.py` và đọc cấu hình từ đây.

Bạn có thể thêm/sửa cấu hình cho trang mới mà không phải sửa code crawler.
"""

from typing import Dict, Iterable, List

from .base import SiteConfig
from .registry import SITE_CONFIG_BUILDERS
from .sites import load_site_modules


def get_supported_sites() -> Dict[str, SiteConfig]:
    """Trả về dict {site_key: SiteConfig} cho tất cả các trang được hỗ trợ."""
    load_site_modules()
    return {
        key: SITE_CONFIG_BUILDERS[key]() for key in sorted(SITE_CONFIG_BUILDERS)
    }


def list_site_keys() -> List[str]:
    """Danh sách key của các site, dùng cho CLI help."""
    return sorted(get_supported_sites().keys())


def get_site_config(site_key: str) -> SiteConfig:
    """Lấy cấu hình cho 1 site, raise KeyError nếu không tồn tại."""
    sites = get_supported_sites()
    try:
        return sites[site_key]
    except KeyError as exc:
        raise KeyError(
            f"Unknown site '{site_key}'. Supported sites: {', '.join(sorted(sites))}"
        ) from exc


def iter_site_configs(keys: Iterable[str] | None = None) -> Iterable[SiteConfig]:
    """Iterator trả về các cấu hình theo danh sách key (hoặc tất cả nếu None)."""
    sites = get_supported_sites()
    if keys is None:
        yield from sites.values()
        return
    for key in keys:
        if key not in sites:
            raise KeyError(
                f"Unknown site '{key}'. Supported sites: {', '.join(sorted(sites))}"
            )
        yield sites[key]
