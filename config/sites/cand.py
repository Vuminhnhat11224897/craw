from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("cand")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://cand.com.vn (Báo Công an nhân dân).

    - Category dạng /{slug}/.
    - Bài viết có URL kết thúc bằng "-i<id>/".
    """

    return SiteConfig(
        key="cand",
        base_url="https://cand.com.vn",
        home_path="/",
        category_path_pattern="/{slug}/",
        article_name="cand",
        max_categories=40,
        max_articles_per_category=80,
        deny_category_prefixes=(
            "/topic",
            "/rssfeed",
            "/eMagazine",
            "/emagazine",
            "/video",
            "/Video",
            "/clip",
            "/Clip",
            "/search",
            "/tags",
            "/tag",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_path_regexes=(r"-i\d+/?$",),
        article_link_selector=".box-title a[href]",
        description_selectors=(
            "div.box-des-detail",
        ),
    )

