from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("moh")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://moh.gov.vn (Cổng thông tin điện tử Bộ Y tế).

    Ghi chú:
    - Trang (thường) dùng Liferay, category nằm dưới prefix /web/guest/<slug>.
    - Bài viết chi tiết thường có path chứa "/-/" hoặc đuôi .html/.htm/.aspx.
    - Category mặc định được ép về "yte" theo yêu cầu phân loại downstream.
    """

    return SiteConfig(
        key="moh",
        base_url="https://moh.gov.vn",
        home_path="/",
        category_path_pattern="/web/guest/{slug}",
        canonicalize_category_paths=False,
        article_name="moh",
        forced_category_id="yte",
        forced_category_name="yte",
        max_categories=30,
        max_articles_per_category=80,
        max_retries=5,
        retry_backoff=1.5,
        allow_category_prefixes=(),
        deny_exact_paths=(
            "/",
        ),
        # Tránh lấy nhầm link bài viết (có đuôi .html/.htm/.aspx) làm category.
        deny_category_path_regexes=(
            r"^/.+\\.(?:html|htm|aspx)$",
            r"/-/",
        ),
        deny_category_prefixes=(
            "/sitemap",
            "/rss",
            "/search",
            "/tim-kiem",
            "/web/guest/-",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_path_regexes=(
            r"^/web/guest/-/",
            r"\\.html$",
            r"\\.htm$",
            r"\\.aspx$",
            r"/-/",
        ),
        article_link_selector="a[href*='/web/guest/-/'], a[href*='/-/'], a[href$='.html'], a[href$='.htm'], a[href$='.aspx']",
        delay_seconds=1.0,
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        # moh.gov.vn hiện trả về handshake với DH key nhỏ, OpenSSL 3 mặc định từ chối.
        allow_weak_dh_ssl=True,
    )

