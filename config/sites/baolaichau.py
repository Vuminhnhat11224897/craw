from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baolaichau")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baolaichau.vn (Báo Lai Châu điện tử).

    - Category dạng /{slug}.
    - Bài viết có dạng /{category}/{slug}-{id}.
    - Link bài viết thường dùng class "blc-post__link".
    """

    return SiteConfig(
        key="baolaichau",
        base_url="https://baolaichau.vn",
        home_path="/",
        category_path_pattern="/{slug}",
        article_name="baolaichau",
        max_categories=30,
        max_articles_per_category=80,
        deny_category_prefixes=(
            "/video",
            "/multimedia",
            "/infographic",
            "/quang-cao",
            "/tags",
        ),
        deny_exact_paths=("/",),
        allowed_article_path_regexes=(r"-\d+/?$",),
        article_link_selector="a.blc-post__link[href]",
    )

