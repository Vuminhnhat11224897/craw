from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("laocai")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://laocai.gov.vn (Cổng TTĐT tỉnh Lào Cai, nền VNPT Portal).

    - Chỉ crawl chuyên mục Tin thời sự (/tin-thoi-su).
    - Bài viết chi tiết có URL dạng /<category>/<slug>-<id>.
    """

    return SiteConfig(
        key="laocai",
        base_url="https://laocai.gov.vn",
        home_path="/",
        article_name="laocai",
        allow_category_prefixes=(
            "/tin-thoi-su",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_path_regexes=(
            r"^/tin-thoi-su/[a-z0-9-]+-\d+/?$",
        ),
        article_link_selector="h2.Title a[href], ul.ArticleList a[href]",
    )
