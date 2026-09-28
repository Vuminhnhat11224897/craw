from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baotuyenquang")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baotuyenquang.com.vn (Báo Tuyên Quang điện tử).

    - Category có thể là nhiều cấp (vd: /thoi-su-chinh-tri/tin-tuc/).
    - Bài viết có dạng /{category...}/{YYYYMM}/{slug}/ (thường có hậu tố -id).
    """

    return SiteConfig(
        key="baotuyenquang",
        base_url="https://baotuyenquang.com.vn",
        home_path="/",
        canonicalize_category_paths=False,
        article_name="baotuyenquang",
        category_path_pattern="/{slug}/",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su-chinh-tri",
            "/kinh-te",
            "/xa-hoi",
            "/van-hoa",
            "/an-ninh-quoc-phong",
            "/khoa-hoc-cong-nghe",
            "/quoc-te",
            "/phap-luat",
            "/the-thao-giai-tri",
            "/goc-nhin",
            "/xa-luan-van-de-ky-nay",
            "/tin-noi-bat",
            "/bao-ve-nen-tang-tu-tuong-cua-dang",
            "/dang-trong-cuoc-song-hom-nay",
            "/chuyen-muc-cai-cach-hanh-chinh",
            "/thong-tin-quang-ba",
            "/hoc-tap-theo-bac",
            "/dai-hoi-dang-bo-cac-cap--nhiem-ky-2025-2030",
        ),
        deny_category_prefixes=(
            "/multimedia",
            "/truyen-hinh",
            "/podcast",
            "/doc-bao-in",
            "/nen-tang-so",
            "/tim-kiem",
        ),
        deny_exact_paths=("/",),
        allowed_article_path_regexes=(
            r"/(?:[^/]+/)+\d{6}/[^/]+/?$",
        ),
        deny_article_prefixes=(
            "/multimedia",
            "/truyen-hinh",
            "/podcast",
            "/doc-bao-in",
            "/nen-tang-so",
            "/tim-kiem",
        ),
        article_link_selector=(
            "a.title1[href], a.title2[href], a.title3[href], "
            "a.title4[href], a.title5[href]"
        ),
    )
