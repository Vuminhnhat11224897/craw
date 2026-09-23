from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("khoahocphattrien")
def build_config() -> SiteConfig:
    """
    Cấu hình cho http://khoahocphattrien.vn (Báo Khoa học & Phát triển).

    - Category có dạng /p<group>c<id>/<slug>.htm.
    - Bài viết có dạng /<category>/<slug>/<digits>p<group>c<id>.htm.
    """

    return SiteConfig(
        key="khoahocphattrien",
        base_url="http://khoahocphattrien.vn",
        home_path="/",
        article_name="khoahocphattrien",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/p",
        ),
        deny_category_prefixes=(
            "/Pages",
            "/Scripts",
            "/Images",
            "/ThumbImages",
            "/GetThumbNail.ashx",
        ),
        deny_exact_paths=("/",),
        canonicalize_category_paths=False,
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"^/[^/]+/.+/\d+p\d+c\d+\.htm$",
        ),
        article_link_selector=(
            "article a[href$='.htm'], "
            "h3 a[href$='.htm'], "
            "h2 a[href$='.htm'], "
            ".td-module-title a[href$='.htm']"
        ),
    )
