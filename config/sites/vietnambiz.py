from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vietnambiz")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://vietnambiz.vn (VietnamBiz).

    - Các chuyên mục chính có path dạng /thoi-su.htm, /tai-chinh.htm, ...
    - Bài viết chi tiết có URL đuôi ".htm" với phần cuối "-<id>.htm".
    - Trang category/home hiển thị danh sách bài trong các block với
      tiêu đề nằm trong h2.title, h3.title hoặc div.title > a[data-type='title'].
    - Nội dung sapo/tóm tắt bài chi tiết nằm trong div.vnbcbc-sapo[data-role='sapo'].
    """

    return SiteConfig(
        key="vietnambiz",
        base_url="https://vietnambiz.vn",
        home_path="/",
        category_path_pattern="/{slug}.htm",
        article_name="vietnambiz",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/thoi-su",
            "/du-bao",
            "/hang-hoa",
            "/quoc-te",
            "/tai-chinh",
            "/nha-dat",
            "/chung-khoan",
            "/doanh-nghiep",
            "/kinh-doanh",
        ),
        deny_category_prefixes=(
            "/emagazine",
            "/infographic",
            "/photostory",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_url_suffixes=(".htm",),
        description_selectors=(
            "div.vnbcbc-sapo[data-role='sapo']",
            "div.vnbcbc-sapo",
        ),
        article_link_selector=(
            "h2.title a[href], "
            "h3.title a[href], "
            "div.title > a[data-type='title']"
        ),
    )

