from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("conganlaocai")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://congan.laocai.gov.vn (Cổng TTĐT Công an tỉnh Lào Cai, nền VNPT Portal).

    - Category có path một cấp dạng /<slug> (vd. /an-ninh-trat-tu).
    - Bài viết chi tiết có URL dạng /<category>/<slug>-<id>.
    - Link chia sẻ Facebook gắn ?fbclid=..., bỏ query khi chuẩn hóa (mặc định).
    """

    return SiteConfig(
        key="conganlaocai",
        base_url="https://congan.laocai.gov.vn",
        home_path="/",
        article_name="conganlaocai",
        deny_category_prefixes=(
            "/gioi-thieu",
            "/chuc-nang-nhiem-vu-va-quyen-han",
            "/qua-trinh-xay-dung-chien-dau-va-truong-thanh",
            "/to-chuc-bo-may",
            "/danh-ba-dien-thoai-thu-dien-tu",
            "/so-do-cong-thong-tin-dien-tu",
            "/thong-ke",
            "/thu-tuc-hanh-chinh",
            "/cong-bo-thu-tuc-hanh-chinh",
            "/van-ban-quy-pham-phap-luat",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_path_regexes=(
            r"^/[a-z0-9-]+/[a-z0-9-]+-\d+/?$",
        ),
        article_link_selector="h2.Title a[href], ul.ArticleList a[href]",
    )
