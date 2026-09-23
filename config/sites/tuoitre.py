from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("tuoitre")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://tuoitre.vn.

    - Category thường có path dạng /thoi-su.htm, /kinh-doanh.htm, ...
    - Heuristic: ưu tiên path 1 cấp và kết thúc bằng ".htm".
    """

    return SiteConfig(
        key="tuoitre",
        base_url="https://tuoitre.vn",
        home_path="/",
        category_path_pattern="/{slug}.htm",
        article_name="tuoitre",
        description_selectors=(
            "h2.detail-sapo[data-role='sapo']",
            "h2.detail-sapo",
        ),
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
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
            "/cong-nghe",
        ),
        deny_category_prefixes=(
            "/podcast",
            "/video",
        ),
        deny_exact_paths=(
            "/",
        ),
        # Tuổi Trẻ thường dùng <h3 class="title-news"><a ...>
        article_link_selector="h3.title-news a[href], h2.title-news a[href]",
    )

