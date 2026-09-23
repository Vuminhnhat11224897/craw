from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vpcp")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://vpcp.chinhphu.vn (Website Văn phòng Chính phủ).

    Ghi chú:
    - Category/listing thường là các trang *.htm (vd: /thong-tin-hoat-dong.htm).
    - Bài viết chi tiết thường có hậu tố dạng "-<digits>.htm" (vd: ...-115260....htm).
    - Trang có chuyên mục /video nên loại bỏ khỏi tập URL bài viết.
    """

    return SiteConfig(
        key="vpcp",
        base_url="https://vpcp.chinhphu.vn",
        home_path="/",
        canonicalize_category_paths=False,
        article_name="vpcp",
        max_categories=10,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/tin-noi-bat.htm",
            "/thong-tin-hoat-dong.htm",
            "/cong-tac-dang-doan-the.htm",
            "/cong-ttdt-chinh-phu/",
            "/cac-chuyen-muc-dac-biet/",
        ),
        deny_category_prefixes=(
            "/video",
            "/anh",
            "/owa",
        ),
        deny_exact_paths=(
            "/",
        ),
        deny_category_path_regexes=(
            r"^/.+-\d{8,}\.htm$",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"-\d{8,}\.htm$",
        ),
        deny_article_prefixes=(
            "/video",
            "/anh",
        ),
        article_link_selector="a.box-stream-link-title[href], a.box-focus-link-title[href]",
        delay_seconds=0.8,
    )

