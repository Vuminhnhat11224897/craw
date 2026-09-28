from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("qdnd")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://www.qdnd.vn (Báo Quân đội nhân dân).

    - Category chính thường có path dạng /chinh-tri, /quoc-phong-an-ninh, ...
    - Bài viết có slug kết thúc bằng ID số, ví dụ "...-1020977".
    - Sapo nằm trong div.post-summary.
    """

    return SiteConfig(
        key="qdnd",
        base_url="https://www.qdnd.vn",
        home_path="/",
        article_name="qdnd",
        max_categories=40,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/quoc-phong-an-ninh",
            "/da-phuong-tien",
            "/bao-ve-nen-tang-tu-tuong-cua-dang",
            "/phong-chong-dien-bien-hoa-binh",
            "/phong-chong-tu-dien-bien-tu-chuyen-hoa",
            "/kinh-te",
            "/xa-hoi",
            "/van-hoa",
            "/phong-su-dieu-tra",
            "/giao-duc-khoa-hoc",
            "/phap-luat",
            "/ban-doc",
            "/y-te",
            "/the-thao",
            "/quoc-te",
            "/du-lich",
            "/cung-ban-luan",
            "/tien-toi-dai-hoi-xiv-cua-dang",
        ),
        deny_category_prefixes=(
            "/audio",
            "/video",
            "/Lf",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_path_regexes=(r"-\d+/?$",),
        article_link_selector=".list-news a[href]",
        description_selectors=("div.post-summary",),
    )

