from __future__ import annotations

from ..base import SiteConfig, _default_site_config
from ..registry import register_site

@register_site("vietbao")
def build_config() -> SiteConfig:
    return SiteConfig(
        key="vietbao",
        base_url="https://vietbao.vn",
        home_path="/",
        article_name="vietbao",
        deny_exact_paths=("/",),
        allowed_locales=("vi", "vi-vn"),
        deny_article_prefixes=(
            "/en",
            "/en/",
            "/zh-CN",
            "/zh-CN/",
            "/zh-cn",
            "/zh-cn/",
            "/cn",
            "/cn/",
            "/404",
        ),
    )

