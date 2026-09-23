from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("tapchitoaan")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://tapchitoaan.vn (Tạp chí Tòa án nhân dân điện tử).

    - Category chủ yếu là slug đơn: /thoi-su, /nghien-cuu, /xet-xu, ...
    - Bài viết chi tiết có đuôi ".html" và thường kết thúc bằng số ID.
    """

    return SiteConfig(
        key="tapchitoaan",
        base_url="https://tapchitoaan.vn",
        home_path="/",
        article_name="tapchitoaan",
        max_categories=40,
        max_articles_per_category=100,
        allow_category_prefixes=(
            "/an-le",
            "/an-xua",
            "/binh-luan-trao-doi-gop-y",
            "/cac-ban-an-le",
            "/chuyen-phap-dinh",
            "/co-the-ban-can-biet",
            "/cong-dan-va-phap-luat-2",
            "/dan-sinh",
            "/doanh-nhan",
            "/giai-dap-phap-luat",
            "/kinh-doanh",
            "/kinh-te",
            "/nghien-cuu",
            "/nghien-cuu-xay-dung-phap-luat",
            "/nghiencuukhoahocxetxu",
            "/nhan-vat",
            "/nhan-vat-su-kien",
            "/nhin-ra-nuoc-ngoai",
            "/phap-luat-the-gioi",
            "/su-kien",
            "/suy-ngam-cuoi-tuan",
            "/suy-ngam-thoi-su",
            "/thao-go",
            "/theo-don-thu-ban-doc",
            "/thoi-su",
            "/tin-quan-tam",
            "/trao-doi-y-kien",
            "/traodoithuctienkinhnghiemxetxu",
            "/van-de-thoi-su-thoi-su",
            "/van-hoa",
            "/vu-an-trong-diem",
            "/xay-dung-phat-luat",
            "/xet-xu",
            "/xet-xu-cua-hoi-dong-tham-phan",
            "/xet-xu-xet-xu",
        ),
        deny_category_prefixes=(
            "/lienhe",
            "/video",
            "/tap-chi-giay",
            "/tap-chi-toa-an-nhan-dan-dien-tu-khai-truong",
        ),
        deny_exact_paths=("/",),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"\d+\.html$",),
    )
