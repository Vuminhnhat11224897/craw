from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baophapluat")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baophapluat.vn (Báo Pháp luật Việt Nam).

    - Category nằm dưới /chuyen-muc/{slug}.html (một số link không có .html).
    - Bài viết chi tiết có URL dạng "/{slug}.html".
    - Link bài viết thường dùng <a class="loading-link" ...>.
    """

    return SiteConfig(
        key="baophapluat",
        base_url="https://baophapluat.vn",
        home_path="/",
        category_path_pattern="/chuyen-muc/{slug}.html",
        article_name="baophapluat",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chuyen-muc/",
        ),
        deny_category_prefixes=(
            "/chuyen-muc/media",
            "/chuyen-muc/thong-tin-quang-cao",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(
            r"^/[^/]+\.html$",
        ),
        deny_article_prefixes=(
            "/chuyen-muc/",
            "/media/",
            "/podcasts/",
            "/static/",
        ),
        article_link_selector="a.loading-link[href$='.html']",
        description_selectors=(
            "meta[name='description']",
            "meta[property='og:description']",
        ),
    )

