from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baonghean")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baonghean.vn (Báo Nghệ An điện tử).

    - Category dạng /{slug} và có subcategory.
    - Bài viết thường có URL kết thúc bằng -<id>.html hoặc -event<id>.html.
    - Link bài viết trong trang category thường nằm trong .b-grid__title/.b-grid__img.
    """

    return SiteConfig(
        key="baonghean",
        base_url="https://baonghean.vn",
        home_path="/",
        article_name="baonghean",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/kinh-te",
            "/xa-hoi",
            "/the-thao",
            "/suc-khoe",
            "/phap-luat",
            "/quoc-te",
            "/xay-dung-dang",
            "/giao-duc",
            "/giai-tri",
            "/ket-noi-doanh-nghiep",
            "/lao-dong",
        ),
        deny_category_prefixes=(
            "/video",
            "/short-video",
            "/photo",
            "/podcast",
            "/emagazine",
            "/an-pham",
            "/tin-moi-nhat",
            "/thoi-tiet",
            "/lich-am-duong-hom-nay",
            "/cdn-cgi",
            "/assets",
            "/en",
            "/fr",
            "/ru",
            "/cn",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(
            r"-\d+\.html$",
            r"-event\d+\.html$",
        ),
        deny_article_prefixes=(
            "/video",
            "/short-video",
            "/photo",
            "/podcast",
            "/emagazine",
            "/an-pham",
        ),
        article_link_selector=".b-grid__title a[href], .b-grid__img a[href]",
        description_selectors=(
            ".sc-longform-header-sapo",
            "meta[name='description']",
        ),
        allowed_locales=("vi", "vi-vn"),
    )

