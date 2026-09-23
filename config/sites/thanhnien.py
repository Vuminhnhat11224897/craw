from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("thanhnien")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://thanhnien.vn.

    - Category chính có path dạng /thoi-su.htm, /the-gioi.htm, ...
    - Trang category và trang bài đều dùng đuôi .htm, nên giới hạn
      allowed_article_url_suffixes để tránh thu thập các URL không phải bài viết.
    - Ở trang category, danh sách bài dùng thẻ
      <a class="box-category-link-title" data-linktype="newsdetail" ...>,
      vì vậy khai báo article_link_selector để crawler ưu tiên selector này.
    """

    return SiteConfig(
        key="thanhnien",
        base_url="https://thanhnien.vn",
        home_path="/",
        article_name="thanhnien",
        max_categories=30,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinh-tri",
            "/thoi-su",
            "/the-gioi",
            "/kinh-te",
            "/doi-song",
            "/suc-khoe",
            "/gioi-tre",
            "/giao-duc",
            "/du-lich",
            "/van-hoa",
            "/giai-tri",
            "/the-thao",
            "/cong-nghe",
            "/xe",
            "/tieu-dung-thong-minh",
        ),
        deny_category_prefixes=(
            "/video",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_article_url_suffixes=(".htm",),
        article_link_selector="a.box-category-link-title[data-linktype='newsdetail']",
    )

