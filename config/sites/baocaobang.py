from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baocaobang")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baocaobang.vn (Báo Cao Bằng điện tử).

    - Category chính trên menu có dạng /Thoi-su, /chinh-tri, ...
    - Bài viết chi tiết có URL đuôi ".html" với slug kết thúc bằng "-<id>.html".
    """

    return SiteConfig(
        key="baocaobang",
        base_url="https://baocaobang.vn",
        home_path="/",
        article_name="baocaobang",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/Thoi-su",
            "/chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/van-hoa",
            "/the-thao",
            "/Khoa-hoc-Cong-nghe",
            "/Quoc-phong-An-ninh",
            "/Suc-khoe-Doi-song",
            "/The-gioi",
            "/Giao-duc",
            "/Ky-Phong-su",
        ),
        deny_category_prefixes=(
            "/Truyenhinh-Internet",
            "/Thong-tin-Toa-soan",
            "/Phongsuanh",
            "/Du-bao-thoi-tiet-Cao-Bang",
            "/tin-noi-bat",
            "/tin-tieu-diem",
            "/multimedia",
            "/search",
            "/tags",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-\d+\.html$",),
        article_link_selector="article a[href], h3 a[href], h2 a[href], .card-title a[href]",
    )

