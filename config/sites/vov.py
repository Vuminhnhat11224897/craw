from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vov")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://vov.vn (Báo điện tử VOV).

    Tạm thời sử dụng cấu hình mặc định, dựa vào heuristic chung để:
    - phát hiện category từ các link nội bộ trên trang chủ,
    - phát hiện link bài viết trong trang category.
    Nếu cần tối ưu thêm (selector description, danh sách category cụ thể, ...),
    có thể tinh chỉnh cấu hình này sau khi đã thu thập được dữ liệu mẫu.
    """

    return SiteConfig(
        key="vov",
        base_url="https://vov.vn",
        home_path="/",
        article_name="vov",
        deny_exact_paths=("/",),
    )

