from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site

@register_site("cand_vn")
def build_config() -> SiteConfig:
    """
    Cấu hình cho https://cand.vn (Báo Công an nhân dân, domain mới).

    - cand.com.vn hiện redirect 302 về cand.vn; config "cand" cũ vẫn giữ nguyên.
    - Category dạng /{slug}/, có cấp con (vd. /cong-an/hoat-dong-ll-cand/).
    - Bài viết có URL dạng "/<slug>-post<id>.html".
    """

    return SiteConfig(
        key="cand_vn",
        base_url="https://cand.vn",
        home_path="/",
        category_path_pattern="/{slug}/",
        # Cùng nguồn báo với cand.com.vn nên giữ chung article_name.
        article_name="cand",
        max_categories=40,
        max_articles_per_category=80,
        deny_category_prefixes=(
            "/chu-de",
            "/rss",
            "/emagazine",
            "/multimedia",
            "/video",
            "/podcast",
            "/tin-anh",
            "/infographic",
            "/lien-he",
            "/an-ninh-the-gioi",
            "/van-nghe-cong-an",
        ),
        deny_exact_paths=(
            "/",
        ),
        allowed_locales=("vi", "vi-vn"),
        allowed_article_path_regexes=(r"-post\d+\.html$",),
        article_link_selector=".story__heading a[href]",
        description_selectors=(
            "div.article__sapo",
        ),
    )
