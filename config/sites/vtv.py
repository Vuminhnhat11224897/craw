from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vtv")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://vtv.vn.

    Thực tế VTV có thể phục vụ nội dung qua cả vtv.gov.vn và vtv.vn, nên cấu hình
    cho phép host suffix của cả 2 domain để tránh bỏ sót link bài.
    """

    return _default_site_config(
        "vtv",
        "https://vtv.vn",
        allowed_locales=("vi", "vi-vn"),
        allowed_internal_host_suffixes=(
            "vtv.vn",
            "vtv.gov.vn",
        ),
        allowed_article_host_suffixes=(
            "vtv.vn",
            "vtv.gov.vn",
        ),
        allowed_article_url_suffixes=(
            ".htm",
            ".html",
        ),
    )

