from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("thanhtra")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://thanhtra.gov.vn (Cổng TTĐT Thanh tra Chính phủ).

    Ghi chú:
    - Site dùng Liferay, category nằm dưới prefix /web/guest/<slug>.
    - Link bài viết chi tiết có dạng:
      /web/guest/xem-chi-tiet-tin-tuc/-/asset_publisher//Content/<slug>?<id>
      (query dạng "?<id>" là bắt buộc để server render đúng nội dung).
    """

    return SiteConfig(
        key="thanhtra",
        base_url="https://thanhtra.gov.vn",
        home_path="/",
        category_path_pattern="/web/guest/{slug}",
        article_name="thanhtra",
        max_categories=20,
        max_articles_per_category=80,
        keep_query_params=True,
        allow_category_prefixes=(
            "/web/guest/thanh-tra",
            "/web/guest/khieu-nai-to-cao",
            "/web/guest/phong-chong-tham-nhung",
            "/web/guest/tin-tong-hop",
            "/web/guest/thong-bao",
            "/web/guest/tin-hinh-anh",
        ),
        deny_category_prefixes=(
            "/web/guest/xem-chi-tiet-tin-tuc",
            "/web/guest/trang-chu",
            "/web/guest/tim-kiem",
        ),
        deny_exact_paths=(
            "/",
            "/web/guest",
            "/web/guest/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_path_regexes=(
            r"^/web/guest/xem-chi-tiet-tin-tuc/-/asset_publisher/+[Cc]ontent/.+",
        ),
        # Tránh lấy nhầm trang giới thiệu lẫn trong menu.
        deny_article_prefixes=(
            "/web/guest/xem-chi-tiet-tin-tuc/-/asset_publisher/Content/chuc-nang-nhiem",
            "/web/guest/xem-chi-tiet-tin-tuc/-/asset_publisher//Content/chuc-nang-nhiem",
        ),
        article_link_selector=(
            "a[href*='/xem-chi-tiet-tin-tuc/-/asset_publisher']"
            "[href*='Content'][href*='?']"
        ),
    )

