from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("baodongnai")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="baodongnai",
        base_url="https://baodongnai.com.vn",
        home_path="/",
        article_name="baodongnai",
        max_categories=30,
        deny_exact_paths=("/",),
        deny_category_prefixes=(
            "/media",
            "/video-clip",
            "/podcast",
            "/anh-dep",
            "/tim-kiem",
            "/common",
            "/file",
        ),
        allowed_article_path_regexes=(
            r"/\d{6}/[a-z0-9-]+-[a-f0-9]{7}/?$",
        ),
        deny_article_prefixes=(
            "/video-clip",
            "/media/infographic",
            "/media/megastory",
            "/podcast",
            "/anh-dep",
            "/file",
            "/common",
        ),
        article_link_selector="a.title1[href], a.title3[href]",
        description_selectors=(
            "div#content.content-detail .td-post-content > p",
            "div#content.content-detail p",
        ),
    )

