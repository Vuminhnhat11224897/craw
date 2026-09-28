from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vnexpress")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://vnexpress.net.

    - Category thường có path dạng /thoi-su, /the-gioi, ...
    - Dùng heuristic: chỉ lấy các path 1 cấp ("/abc") và không nằm trong danh sách deny.
    - Ở trang category, VNExpress dùng thẻ <article class="item-news">,
      nên ta khai báo article_link_selector để crawler ưu tiên selector này.
    """

    return SiteConfig(
        key="vnexpress",
        category_pagination_url_template="{category_path}-p{page}",
        base_url="https://vnexpress.net",
        home_path="/",
        article_name="vnexpress",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/goc-nhin",
            "/the-gioi",
            "/kinh-doanh",
            "/giai-tri",
            "/the-thao",
            "/phap-luat",
            "/giao-duc",
            "/suc-khoe",
            "/doi-song",
            "/du-lich",
            "/khoa-hoc",
            "/so-hoa",
            "/oto-xe-may",
            "/y-kien",
            "/tam-su",
        ),
        deny_category_prefixes=(
            "/video",
            "/podcast",
            "/infographics",
            "/interactive",
        ),
        deny_exact_paths=(
            "/",
        ),
        deny_category_path_regexes=(
            r"^/chuyen-muc/.+-\\d{4,}\\.htm$",
        ),
        allowed_article_url_suffixes=(),
        article_link_selector="article.item-news a[href]",
    )

