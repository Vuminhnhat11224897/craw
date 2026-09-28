from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("moit")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://moit.gov.vn (Cổng thông tin điện tử Bộ Công Thương).

    - Category chính nằm dưới /tin-tuc/<slug>.
    - Bài viết chi tiết có URL đuôi ".html" dưới /tin-tuc/.
    """

    return SiteConfig(
        key="moit",
        base_url="https://moit.gov.vn",
        home_path="/",
        category_path_pattern="/tin-tuc/{slug}",
        article_name="moit",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/tin-tuc",
        ),
        deny_exact_paths=(
            "/",
            "/tin-tuc",
            "/tin-tuc/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"^/tin-tuc/.+\.html$",),
        article_link_selector="a[href*='/tin-tuc/'][href$='.html']",
        description_selectors=(
            "div.article-brief",
            "meta[name='description']",
            "meta[property='og:description']",
        ),
    )

