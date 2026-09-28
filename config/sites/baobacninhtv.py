from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baobacninhtv")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baobacninhtv.vn (Báo Bắc Ninh).

    - Category dạng /{slug}.
    - Bài viết có URL đuôi .bbg với pattern "-postid<id>.bbg".
    - Sapo trong div.news_detail_sapo.
    """

    return SiteConfig(
        key="baobacninhtv",
        base_url="https://baobacninhtv.vn",
        home_path="/",
        article_name="baobacninhtv",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/xay-dung-dang",
            "/chinh-tri-bao-ve-nen-tang-tu-tuong-cua-dang",
            "/chinh-tri-nhan-su-moi",
            "/kinh-te",
            "/xa-hoi",
            "/doi-song",
            "/phap-luat",
            "/an-toan-giao-thong",
            "/suc-khoe",
            "/giao-duc",
            "/quoc-phong",
            "/the-gioi",
            "/the-thao",
            "/the-thao-nhat-ky-sea-games-33",
            "/nhip-song-tre",
            "/nhip-song-tre-guong-mat",
            "/nhip-song-tre-thanh-nien-cong-nhan",
            "/dat-va-nguoi-bac-ninh",
            "/van-hoa-goc-cho-nguoi-yeu-tho",
            "/van-hoa-tac-gia-tac-pham",
            "/phong-tuc-tap-quan",
            "/sukien",
            "/mon-ngon",
            "/bacgiang-van-hoa",
            "/moi-nhat",
        ),
        deny_category_prefixes=(
            "/multimedia",
            "/podcast",
            "/photo",
            "/videos",
            "/infographics",
            "/thong-tin-quang-cao",
            "/bacgiang-emagazine",
            "/bg2",
            "/bando",
        ),
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".bbg",),
        allowed_article_path_regexes=(r"-postid\d+\.bbg$",),
        deny_article_prefixes=(
            "/bg/infographics",
            "/photo",
            "/videos",
            "/podcast",
        ),
        article_link_selector="a.font-tin-doc[href]",
        description_selectors=(
            "div.news_detail_sapo p",
            "div.news_detail_sapo",
        ),
    )

