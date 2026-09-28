from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("laodong")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://laodong.vn (Báo Lao Động).

    - Bài viết chi tiết có URL đuôi ".ldo" theo các link đã thu thập được
      trong exported_data.
    - Các chuyên mục chính có path dạng /thoi-su, /xa-hoi, /kinh-doanh, ...
    """

    return _default_site_config(
        "laodong",
        "https://laodong.vn",
        allowed_locales=("vi", "vi-vn"),
        allowed_internal_host_suffixes=(
            "laodong.vn",
        ),
        deny_internal_host_prefixes=(
            "news.",
        ),
        allowed_article_host_suffixes=(
            "laodong.vn",
        ),
        deny_article_host_prefixes=(
            "news.",
        ),
        allowed_article_url_suffixes=(".ldo",),
        allow_category_prefixes=(
            "/thoi-su",
            "/xa-hoi",
            "/kinh-doanh",
            "/bat-dong-san",
            "/van-hoa-giai-tri",
            "/the-gioi",
            "/the-thao",
            "/suc-khoe",
            "/media",
            "/cong-doan",
            "/xe",
            "/phap-luat",
            "/giao-duc",
            "/y-te",
            "/su-kien-binh-luan",
        ),
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
