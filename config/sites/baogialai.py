from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baogialai")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baogialai.com.vn.

    - Category dạng /{slug}/.
    - Bài viết chi tiết có URL dạng "-post<id>.html".
    """

    return SiteConfig(
        key="baogialai",
        base_url="https://baogialai.com.vn",
        home_path="/",
        article_name="baogialai",
        category_path_pattern="/{slug}/",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su-su-kien",
            "/thoi-su-quoc-te",
            "/thoi-su-binh-luan",
            "/chinh-tri",
            "/kinh-te",
            "/giao-duc",
            "/suc-khoe",
            "/van-hoa",
            "/giai-tri",
            "/doi-song",
            "/the-thao",
            "/song-tre-song-dep",
            "/khoa-hoc-cong-nghe",
            "/do-thi",
            "/du-lich",
            "/phap-luat",
            "/tu-thien",
            "/ban-doc",
            "/chuyen-nguoi-gia-lai",
            "/phong-su-ky-su",
            "/xe-may-xe-o-to",
            "/thi-truong-vang",
            "/ma-ra-thon",
            "/tennis-pickleball",
            "/xoa-nha-tam-nha-dot-nat",
            "/ban-tin-the-gioi",
            "/gia-lai-hom-nay",
            "/gia-lai-moi-tuan-mot-diem-den",
            "/diem-den-gia-lai-2022",
            "/net-zero",
            "/rung-bien-ket-noi",
            "/chuyen-dong-tre",
            "/thoi-tiet",
        ),
        deny_category_prefixes=(
            "/bao-anh",
            "/bao-in",
            "/media",
            "/multimedia",
            "/podcast",
            "/thong-tin-quang-cao",
            "/chu-de",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-post\d+\.html$",),
        article_link_selector="article a[href]",
    )

