from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("tienphong")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://tienphong.vn.

    - Bài viết chi tiết có URL đuôi ".tpo" (ví dụ:
      "...-post1806382.tpo"), vì vậy giới hạn suffix này để tránh
      thu thập các trang không phải bài viết.
    - Sapo/description nằm trong div.article__sapo.cms-desc.
    """

    return _default_site_config(
        "tienphong",
        "https://tienphong.vn",
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".tpo",),
        description_selectors=(
            "div.article__sapo",
            "div.article__sapo.cms-desc",
        ),
    )

