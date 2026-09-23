from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("plo")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://plo.vn (Pháp Luật TP.HCM).

    - Category thường có dạng /thoi-su, /phap-luat, /kinh-te, ...
    - Bài viết chi tiết có URL đuôi ".html" và kết thúc bằng "-post<id>.html".
    """

    return SiteConfig(
        key="plo",
        base_url="https://plo.vn",
        home_path="/",
        article_name="plo",
        category_path_pattern="/{slug}/",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/phap-luat",
            "/quoc-te",
            "/an-ninh-trat-tu",
            "/kinh-te-xanh",
            "/kinh-te",
            "/do-thi",
            "/trang-dia-phuong",
            "/xa-hoi",
            "/bat-dong-san",
            "/giao-duc",
            "/y-te",
            "/van-hoa",
            "/giai-tri",
            "/the-thao",
            "/du-lich",
            "/cong-nghe",
            "/ban-doc",
            "/phap-ly-cho-kieu-bao",
        ),
        deny_category_prefixes=(
            "/video",
            "/multimedia",
            "/podcast",
            "/audio",
            "/infographic",
            "/interactive",
            "/photo",
            "/anh",
            "/tags",
            "/tag",
            "/topics",
        ),
        deny_category_path_regexes=(r"-$",),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-post\d+\.html$",),
        article_link_selector="a[href*='-post']",
    )
