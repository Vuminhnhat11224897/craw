from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baohaugiang")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://baohaugiang.com.vn (Báo Hậu Giang Online).

    - Category dạng /{slug}.html với slug có hậu tố id (ví dụ: /thoi-su-215.html).
    - Bài viết có URL dạng /{category}/{slug}-<id>.html.
    """

    return SiteConfig(
        key="baohaugiang",
        base_url="https://baohaugiang.com.vn",
        home_path="/",
        category_path_pattern="/{slug}.html",
        article_name="baohaugiang",
        max_categories=40,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/an-toan-giao-thong-",
            "/ban-doc-",
            "/bao-hiem-xa-hoi-",
            "/bien-dao-viet-nam-",
            "/chinh-tri-",
            "/chuyen-thoi-su-",
            "/cong-thuong-",
            "/cung-phong-chong-toi-pham-",
            "/doan-dai-bieu-quoc-hoi-tinh-hau-giang-",
            "/doanh-nghiep-tu-gioi-thieu-",
            "/doi-song-",
            "/du-lich-",
            "/dua-nghi-quyet-cua-dang-vao-cuoc-song-",
            "/giao-duc-",
            "/goc-suc-khoe-",
            "/hoat-dong-doan-the-",
            "/hoc-tap-va-lam-theo-tam-guong-dao-duc-ho-chi-minh-",
            "/hoi-dong-nhan-dan-tinh-hau-giang-",
            "/khoa-giao-",
            "/khoa-hoc-cong-nghe-",
            "/kinh-te-",
            "/lao-dong-viec-lam-",
            "/mat-tran-to-quoc-viet-nam-tinh-hau-giang-",
            "/moi-truong-",
            "/nong-nghiep-nong-thon-",
            "/phap-luat-",
            "/quoc-phong-an-ninh-",
            "/quoc-te-",
            "/tai-chinh-",
            "/tam-long-vang-",
            "/the-gioi-do-day-",
            "/the-thao-",
            "/the-thao-nuoc-ngoai-",
            "/the-thao-trong-nuoc-",
            "/thoi-su-",
            "/thoi-su-trong-nuoc-",
            "/thoi-su-trong-tinh-",
            "/tim-hieu-phap-luat-",
            "/tin-tuc-",
            "/van-hoa-",
            "/xa-hoi-",
            "/xay-dung-dang-chinh-quyen-",
            "/xay-dung-do-thi-",
            "/y-te-",
        ),
        deny_exact_paths=("/",),
        deny_article_prefixes=(
            "/bang-gia-quang-cao/",
            "/lien-he/",
            "/tim-kiem/",
            "/video/",
            "/multimedia/",
            "/megastory/",
            "/infographics/",
            "/anh/",
            "/podcast/",
            "/foreign-languages/",
        ),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"/[^/]+/[^/]+-\d+\.html$",),
    )

