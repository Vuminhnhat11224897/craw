from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("baovinhlong")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baovinhlong.com.vn.

    - Category dạng /{slug}/ (có thể có subcategory).
    - Bài viết có dạng /{category}/{yyyymm}/{slug}-{id}/ (không .html).
    """

    return SiteConfig(
        key="baovinhlong",
        base_url="https://baovinhlong.com.vn",
        home_path="/",
        article_name="baovinhlong",
        category_path_pattern="/{slug}/",
        canonicalize_category_paths=False,
        max_categories=80,
        max_articles_per_category=80,
        allow_category_prefixes=(),
        deny_category_prefixes=(
            "/tieu-diem",
            "/phong-su-anh",
            "/chinh-tri",
            "/van-hoa-giai-tri",
            "/the-thao",
            "/khoa-hoc-cong-nghe",
            "/the-gioi-tre",
            "/phap-luat",
            "/nhip-song-dong-bang",
            "/chuyen-tu-te",
            "/phong-su-ky-su",
            "/suc-khoe",
            "/thu-gian",
            "/thoi-su/thoi-su-goc-nhin",
            "/quoc-te/tin-tuc",
            "/quoc-te/phan-tich",
            "/chinh-tri/xay-dung-dang",
            "/chinh-tri/lam-theo-guong-bac",
            "/chinh-tri/dua-nghi-quyet-vao-cuoc-song",
            "/kinh-te/cong-nghiep",
            "/kinh-te/nong-nghiep",
            "/kinh-te/thuong-mai-dich-vu",
            "/kinh-te/thi-truong",
            "/xa-hoi/y-te",
            "/xa-hoi/giao-duc-dao-tao",
            "/xa-hoi/hon-nhan-gia-dinh",
            "/xa-hoi/dia-chi-nhan-dao",
            "/xa-hoi/du-lich",
            "/van-hoa-giai-tri/phim-tren-thvl",
            "/van-hoa-giai-tri/tin-tuc-giai-tri",
            "/van-hoa-giai-tri/tac-gia-tac-pham",
            "/the-gioi-tre/hoat-dong-doan-hoi",
            "/the-gioi-tre/nhip-song-online",
            "/the-gioi-tre/thoi-trang",
            "/phap-luat/an-ninh-trat-tu",
            "/phap-luat/chuyen-canh-giac",
            "/phap-luat/toa-an",
            "/phap-luat/tu-van",
            "/ban-doc/dien-dan",
            "/ban-doc/hop-thu",
            "/ban-doc/phan-hoi",
        ),
        deny_exact_paths=("/",),
        allowed_article_path_regexes=(r"-[a-z0-9]+/?$",),
        deny_article_prefixes=("/lien-he",),
    )
