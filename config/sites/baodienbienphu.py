from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodienbienphu")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baodienbienphu.vn.

    - Bài viết có path dạng /tin-bai/{category}/{slug}.
    - Trang chủ có link bài viết, nhưng trang chuyên mục render client-side,
      nên dùng trang chủ làm nguồn thu thập bài.
    """

    return SiteConfig(
        key="baodienbienphu",
        base_url="https://baodienbienphu.vn",
        home_path="/",
        article_name="baodienbienphu",
        category_path_pattern="/tin-tuc/{slug}",
        max_categories=20,
        max_articles_per_category=12,
        article_link_selector="a[href*='/tin-bai/']",
        allowed_article_path_regexes=(
            r"^/tin-bai/[^/]+/[^/]+/?$",
        ),
    )

