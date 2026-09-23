from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("cema")
def build_config() -> SiteConfig:
    """
    Cấu hình cho http://cema.gov.vn (Cổng thông tin điện tử Bộ Dân tộc và Tôn giáo).

    Ghi chú:
    - Site phục vụ qua HTTP; HTTPS hiện lỗi chứng chỉ (hostname mismatch).
    - Trang chuyên mục thường là các URL kết thúc bằng ".htm" (ví dụ: /tin-tuc.htm,
      /tin-tuc/tin-tuc-su-kien/thoi-su-chinh-tri.htm).
    - Bài viết chi tiết thường nằm dưới các prefix như:
      /tin-tuc/<group>/<category>/<article>.htm, /thong-bao/<article>.htm, ...
    """

    return SiteConfig(
        key="cema",
        base_url="http://cema.gov.vn",
        home_path="/home.htm",
        canonicalize_category_paths=False,
        article_name="cema",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/tin-tuc",
            "/tin-tuc-hoat-dong",
            "/thong-bao",
            "/chuyen-doi-so",
        ),
        deny_exact_paths=(
            "/",
        ),
        # Tránh lấy nhầm link bài viết làm category.
        deny_category_path_regexes=(
            r"^/tin-tuc/[^/]+/[^/]+/.+\.htm$",
            r"^/tin-tuc-hoat-dong/.+\.htm$",
            r"^/thong-bao/.+\.htm$",
            r"^/chuyen-doi-so/.+\.htm$",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".htm",),
        allowed_article_path_regexes=(
            r"^/tin-tuc/[^/]+/[^/]+/[^/]+\.htm$",
            r"^/tin-tuc-hoat-dong/[^/]+\.htm$",
            r"^/thong-bao/[^/]+\.htm$",
            r"^/chuyen-doi-so/[^/]+\.htm$",
        ),
        article_link_selector=(
            ".news-block a[href], .news-block-body a[href], .news-block-other a[href]"
        ),
        delay_seconds=1.0,
        max_retries=5,
        retry_backoff=1.5,
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )

