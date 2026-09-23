from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("sggp")
def build_config() -> SiteConfig:
    """
    Cấu hình cơ bản cho https://www.sggp.org.vn (Báo Sài Gòn Giải Phóng).

    - Category có dạng /{slug}/, chủ yếu lấy theo menu chính.
    - Bài viết chi tiết có URL đuôi "-post<id>.html".
    - Trang category hiển thị danh sách bài trong <article class="story">.
    """

    return SiteConfig(
        key="sggp",
        base_url="https://www.sggp.org.vn",
        home_path="/",
        category_path_pattern="/{slug}/",
        article_name="sggp",
        max_categories=40,
        max_articles_per_category=80,
        allow_category_prefixes=(
            "/chinhtri/",
            "/xaydungdang/",
            "/bvnentangtutuongdang/",
            "/caicachhanhchinh/",
            "/quoc-phong-an-ninh/",
            "/chinhtri-doingoai/",
            "/xahoi/",
            "/theodongthoisu/",
            "/sapxepcacdonvihanhchinh/",
            "/xahoi-giaothong/",
            "/xahoi-gt/",
            "/xahoi-tuoitrecuocsong/",
            "/xahoi-moitruong/",
            "/phapluat/",
            "/anninhtrattu/",
            "/tuvanphapluat/",
            "/kinhte/",
            "/thitruongkt/",
            "/xaydungdiaoc/",
            "/kinhte-taichinhchuungkhoan/",
            "/dulichkhampha/",
            "/dautukt/",
            "/kinhte-doanhnghiepdoanhnhan/",
            "/kinhtedoisong24h/",
            "/daphuongtien/",
            "/thegioi/",
            "/thegioi-tieudiem/",
            "/chinhtruongthegioi/",
            "/hosotulieu/",
            "/giaoduc/",
            "/ytesuckhoe/",
            "/ytesuckhoe-antoanthucpham/",
            "/ytesuckhoe-alobacsi/",
            "/vanhoavannghe/",
            "/nhip-song/",
            "/vanhoagiaitri-nhanvat/",
            "/dienanh/",
            "/vanhoagiaitri-sach/",
            "/nhipcaubandoc/",
            "/nhipcaubandoc-ykienbandoc/",
            "/nhipcaubandoc-diendan-thaoluan/",
            "/khoahoc-congnghe/",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-post\d+\.html$",),
        article_link_selector="article.story a[href]",
        description_selectors=("div.article__sapo",),
    )

