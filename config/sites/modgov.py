from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("modgov")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://mod.gov.vn (Cổng TTĐT Bộ Quốc phòng).

    - Category dùng dạng /home/news?... với query param urile=wcm:path:...
    - Bài viết chi tiết dùng /home/detail?... với query param urile=wcm:path:...
    """

    return SiteConfig(
        key="modgov",
        base_url="https://mod.gov.vn",
        home_path="/home",
        article_name="modgov",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/home/news",
            "/home/news/td",
            "/home/news/event",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_path_regexes=(r"^/home/detail$",),
        keep_query_params=True,
    )

