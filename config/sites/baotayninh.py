from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baotayninh")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://www.baotayninh.vn (Báo Tây Ninh Online).

    - Category dạng /{slug}/, có thể có subcategory.
    - Bài viết có URL đuôi ".html" với slug "-a<id>.html".
    - Sapo thường nằm trong h4.sapo.
    - Link bài trong trang category dùng thẻ a.title.
    """

    return SiteConfig(
        key="baotayninh",
        base_url="https://www.baotayninh.vn",
        home_path="/",
        category_path_pattern="/{slug}/",
        article_name="baotayninh",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su-chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/phap-luat",
            "/quoc-te",
            "/van-hoa-giai-tri",
            "/the-thao",
            "/cong-nghe",
            "/y-te-suc-khoe",
            "/dia-phuong",
            "/trong-tinh",
            "/su-kien",
        ),
        deny_category_prefixes=(
            "/video",
            "/audio",
            "/longform",
            "/image",
            "/xem-bao",
        ),
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-a\d+\.html$",),
        deny_article_prefixes=(
            "/longform",
            "/video",
            "/audio",
            "/image",
            "/xem-bao",
            "/albumphoto",
        ),
        article_link_selector="a.title[href]",
        description_selectors=(
            "h4.sapo",
            "p.sapo",
        ),
    )

