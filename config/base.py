from __future__ import annotations

"""
Định nghĩa cấu trúc SiteConfig và helper dùng chung cho các site.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(slots=True)
class SiteConfig:
    """Cấu hình crawl cho 1 trang báo."""

    # Tên ngắn dùng trong CLI / logging, ví dụ: "vnexpress"
    key: str
    # Base URL, ví dụ "https://vnexpress.net"
    base_url: str

    # Đường dẫn trang chủ tương đối (mặc định "/")
    home_path: str = "/"

    # Mẫu path canonical cho category, dùng slug:
    # ví dụ "/{slug}" (mặc định), hoặc "/{slug}.htm" cho một số site như Tuổi Trẻ.
    category_path_pattern: str = "/{slug}"

    # Nếu True (mặc định), crawler sẽ chuẩn hoá URL category theo `category_path_pattern`.
    # Một số site (vd. Liferay) có thể link category ở nhiều dạng path khác nhau; khi đó
    # có thể tắt để giữ nguyên path discover được trên trang chủ.
    canonicalize_category_paths: bool = True

    # Tên nguồn báo lưu trong cột Article.article_name (ví dụ: "vnexpress")
    article_name: str | None = None

    # Giới hạn số lượng category & số lượng bài / category để tránh crawl quá nhiều.
    max_categories: int = 20
    max_articles_per_category: int = 100

    # Các rule lọc category trên trang chủ:
    # - chỉ lấy link nội bộ có path bắt đầu bằng 1 trong các prefix này (nếu không rỗng)
    # - loại trừ các path bắt đầu bằng 1 trong các prefix này.
    allow_category_prefixes: Tuple[str, ...] = field(default_factory=tuple)
    deny_category_prefixes: Tuple[str, ...] = field(default_factory=tuple)

    # Một số path không phải category (video, podcast, ...) sẽ bỏ qua.
    deny_exact_paths: Tuple[str, ...] = field(default_factory=tuple)

    # Loại bỏ các category có path khớp regex (nếu rỗng sẽ bỏ qua lọc).
    deny_category_path_regexes: Tuple[str, ...] = field(default_factory=tuple)

    # Selector ưu tiên để tìm link bài viết trong trang category (nếu rỗng sẽ dùng heuristic chung).
    article_link_selector: str | None = None

    # Các selector ưu tiên để lấy description/sapo của bài viết (nếu rỗng sẽ dùng heuristic chung).
    description_selectors: Tuple[str, ...] = field(default_factory=tuple)

    # Chỉ chấp nhận các locale/language cụ thể (ví dụ: ("vi", "vi-vn")).
    allowed_locales: Tuple[str, ...] = field(default_factory=tuple)

    # Cho phép crawl category (internal link) trên các host phụ/alias.
    # Mặc định chỉ chấp nhận base_host (từ base_url) và biến thể www.
    allowed_internal_host_suffixes: Tuple[str, ...] = field(default_factory=tuple)
    # Loại bỏ các host nội bộ có prefix nhất định (vd. "news.", "m.").
    deny_internal_host_prefixes: Tuple[str, ...] = field(default_factory=tuple)

    # Nếu fetch category bị 404, thử fallback bằng cách strip các suffix này khỏi path
    # (ví dụ "/tin-tuc.htm" -> "/tin-tuc"). Hữu ích với site thay đổi canonical URL.
    category_fetch_fallback_strip_suffixes: Tuple[str, ...] = field(default_factory=tuple)

    # Chỉ chấp nhận các host bài viết có hậu tố (suffix) nhất định, ví dụ: (".vn",)
    allowed_article_host_suffixes: Tuple[str, ...] = field(default_factory=tuple)
    # Loại bỏ các host bài viết có prefix nhất định (vd. "news.", "m.").
    deny_article_host_prefixes: Tuple[str, ...] = field(default_factory=tuple)

    # Chỉ lấy link bài viết có đuôi (suffix) cụ thể, ví dụ: (".html",)
    allowed_article_url_suffixes: Tuple[str, ...] = field(default_factory=tuple)

    # Chỉ lấy link bài viết có path khớp regex (nếu rỗng sẽ bỏ qua lọc theo path).
    allowed_article_path_regexes: Tuple[str, ...] = field(default_factory=tuple)

    # Loại bỏ các bài viết có path bắt đầu bằng những prefix này.
    deny_article_prefixes: Tuple[str, ...] = field(default_factory=tuple)

    # Giữ lại query string khi chuẩn hóa URL (mặc định loại bỏ).
    keep_query_params: bool = False

    # Override timeout (giây) cho request nếu site chậm phản hồi.
    timeout_seconds: int | None = None

    # Delay giữa các request (giây), dùng để hạn chế rate limit/anti-bot.
    delay_seconds: float | None = None

    # Số lần retry cho HTTP 429/5xx và các lỗi mạng tạm thời.
    max_retries: int = 2

    # Hệ số backoff giữa các lần retry: sleep = retry_backoff * 2**attempt.
    retry_backoff: float = 1.0

    # Các marker text báo hiệu bị chặn, dùng để retry.
    blocked_content_markers: Tuple[str, ...] = field(default_factory=tuple)

    # Header bổ sung cho request (ví dụ User-Agent đặc thù).
    request_headers: Dict[str, str] = field(default_factory=dict)

    # Một số site cấu hình TLS lỗi thời có thể gây lỗi handshake trên OpenSSL mới.
    # Bật các flag này chỉ khi thật sự cần cho site tương ứng.
    allow_legacy_ssl: bool = False
    allow_weak_dh_ssl: bool = False
    # Bỏ qua verify certificate cho các site có chain lỗi (chỉ dùng khi cần thiết).
    allow_insecure_ssl: bool = False

    # Nếu cấu hình, sẽ ép category_id/category_name của mọi bài viết về giá trị này
    # (dùng khi hệ thống downstream cần phân loại cố định theo nguồn).
    forced_category_id: str | None = None
    forced_category_name: str | None = None

    # Optional template for manual backfill pagination (not used by main cron crawl).
    category_pagination_url_template: str | None = None

    def resolved_article_name(self) -> str:
        """Giá trị cuối cùng để ghi vào Article.article_name."""
        if self.article_name:
            return self.article_name
        # Mặc định dùng key nếu không cấu hình riêng.
        return self.key


def _default_site_config(
    key: str,
    base_url: str,
    *,
    article_name: str | None = None,
    **overrides: Any,
) -> SiteConfig:
    """
    Cấu hình mặc định dùng chung cho các trang báo có cấu trúc đơn giản.

    Nếu cần tuỳ biến thêm (prefix category, selector description, ...), tạo hàm
    riêng thay vì dùng helper này.
    """

    return SiteConfig(
        key=key,
        base_url=base_url,
        home_path="/",
        article_name=article_name or key,
        deny_exact_paths=("/",),
        **overrides,
    )
