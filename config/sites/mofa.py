from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("mofa")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://mofa.gov.vn (Cổng thông tin Bộ Ngoại Giao).

    - Category chủ yếu có path dạng /tin-..., /hoat-dong-...
    - Bài viết chi tiết dùng path /tin-chi-tiet/chi-tiet/<slug>-<id>-<cat>.html.
    """

    return SiteConfig(
        key="mofa",
        base_url="https://mofa.gov.vn",
        home_path="/",
        article_name="mofa",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/tin-",
            "/hoat-dong-",
        ),
        deny_category_prefixes=(
            "/tin-chi-tiet",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_path_regexes=(
            r"^/tin-chi-tiet/chi-tiet/.+-\d+(?:-\d+)?\.html$",
        ),
        article_link_selector="a[href*='/tin-chi-tiet/chi-tiet/']",
        description_selectors=(
            "div.article-summary",
        ),
    )

