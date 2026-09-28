from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("znews")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://znews.vn (Zing News).

    - Các chuyên mục chính có path dạng /xuat-ban.html, /kinh-doanh-tai-chinh.html, ...
    - Bài viết chi tiết có URL đuôi ".html" với slug "-post<id>.html".
    - Trang category và trang chủ hiển thị danh sách bài trong
      <article class="article-item"> với tiêu đề trong h3.article-title > a.
    - Nội dung bài chi tiết dùng phần tóm tắt trong p.the-article-summary.
    """

    return SiteConfig(
        key="znews",
        base_url="https://znews.vn",
        home_path="/",
        article_name="znews",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/xuat-ban",
            "/kinh-doanh-tai-chinh",
            "/suc-khoe",
            "/the-thao",
            "/doi-song",
            "/cong-nghe",
            "/giai-tri",
            "/sach-hay",
            "/du-lich",
            "/oto-xe-may",
            "/cuon-sach-toi-doc",
            "/van-hoa-doc",
            "/xa-hoi",
            "/phap-luat",
            "/the-gioi",
            "/giao-duc",
        ),
        deny_category_prefixes=(
            "/video",
            "/series",
            "/tieu-diem",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_url_suffixes=(".html",),
        # Danh sách bài trên category/home: <article class="article-item"> với
        # tiêu đề trong h3.article-title > a.
        article_link_selector="article.article-item h3.article-title a[href]",
        # Tóm tắt bài chi tiết: <p class="the-article-summary">...</p>
        description_selectors=(
            "p.the-article-summary",
        ),
    )

