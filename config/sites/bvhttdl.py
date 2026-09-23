from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("bvhttdl")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://bvhttdl.gov.vn (Cổng thông tin Bộ VHTT&DL).

    - Category chủ yếu dạng /<slug>.htm (vd: /tin-tuc-va-su-kien.htm).
    - Bài viết chi tiết thường là URL root-level kết thúc bằng số dạng timestamp:
      /<slug>-<16-17digits>.htm
    - Một số trang dạng "-t<id>.htm" là trang tổng hợp/chuyên đề, không phải bài viết.
    """

    return SiteConfig(
        key="bvhttdl",
        base_url="https://bvhttdl.gov.vn",
        home_path="/",
        category_path_pattern="/{slug}.htm",
        article_name="bvhttdl",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/tin-tuc-va-su-kien",
            "/su-kien-trang-chu",
            "/van-hoa",
            "/the-ducthe-thao",
            "/du-lich",
            "/gia-dinh",
            "/bao-chi-xuat-ban",
        ),
        deny_exact_paths=(
            "/",
        ),
        deny_category_path_regexes=(
            r"^/.+-\d{14,17}\.htm$",
            r"^/.+-t\d+\.htm$",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"^/[^/]+-\d{14,17}\.htm$",
        ),
        article_link_selector="a[href$='.htm']",
        description_selectors=(
            "p.sapo",
        ),
    )

