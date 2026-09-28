from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baolamdong")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baolamdong.vn.

    - Category dạng /{slug}, có thể có subcategory.
    - Bài viết mới dùng slug kết thúc "-<id>.html".
    - Một số bài cũ có thể dùng dạng /{category}/{yyyymm}/{slug}/.
    """

    return SiteConfig(
        key="baolamdong",
        base_url="https://baolamdong.vn",
        home_path="/",
        article_name="baolamdong",
        category_path_pattern="/{slug}",
        max_categories=20,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/thoi-su",
            "/kinh-te",
            "/doi-song",
            "/phap-luat",
            "/quoc-phong-an-ninh",
            "/van-hoa-giai-tri",
            "/du-lich",
            "/chinh-sach",
            "/cong-nghe-chuyen-doi-so",
            "/tin-tuc-24h",
        ),
        deny_category_prefixes=(
            "/video",
            "/an-pham",
            "/dang-nhap",
            "/tim-kiem",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(
            r"-\d+\.html$",
            r"/\d{6}/[^/]+/?$",
        ),
    )
