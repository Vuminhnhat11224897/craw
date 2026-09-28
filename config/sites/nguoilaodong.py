from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("nguoilaodong")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://nld.com.vn (Báo Người Lao Động).

    Hiện tại trang chủ trả về trang captcha chống DDoS, nên tạm thời dùng
    cấu hình mặc định và heuristic chung, chỉ giới hạn đuôi URL bài viết
    là ".htm" theo các link đã thu thập được trong dữ liệu xuất.
    """

    return _default_site_config(
        "nguoilaodong",
        "https://nld.com.vn",
        allowed_article_url_suffixes=(".htm",),
    )

