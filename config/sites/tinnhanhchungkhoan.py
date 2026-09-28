from __future__ import annotations

from ..base import SiteConfig
from ..registry import register_site


@register_site("tinnhanhchungkhoan")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="tinnhanhchungkhoan",
        base_url="https://www.tinnhanhchungkhoan.vn",
        home_path="/",
        canonicalize_category_paths=False,
        article_name="tinnhanhchungkhoan",
        deny_exact_paths=("/",),
        # Detail pages use "...-post<id>.html".
        allowed_article_url_suffixes=(".html",),
        allowed_article_path_regexes=(r"-post\d+\.html$",),
        article_link_selector="a[href*='-post'][href$='.html']",
    )
