from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Dict, Tuple

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


@dataclass(frozen=True, slots=True)
class ArticleSiteConfig:
    """Configuration overrides for extracting article details from specific hosts."""

    title_selectors: Tuple[str, ...] = ()
    description_selectors: Tuple[str, ...] = ()
    main_container_selectors: Tuple[str, ...] = ()
    main_container_keywords: Tuple[str, ...] = ()
    excluded_section_selectors: Tuple[str, ...] = ()
    inline_image_container_selectors: Tuple[str, ...] = ()
    category_extractors: Tuple[str, ...] = ()
    tag_extractors: Tuple[str, ...] = ()
    inline_media_only: bool = False
    include_metadata_images: bool = False
    allow_extensionless_images: bool = False
    excluded_image_urls: Tuple[str, ...] = ()


_SITE_CONFIG_DIR = Path(__file__).with_name("site_configs")
_SITE_CONFIG_PATH = Path(__file__).with_name("site_config.yml")
_FIELD_DEFS = fields(ArticleSiteConfig)
_ALLOWED_FIELDS = {field.name for field in _FIELD_DEFS}
_TUPLE_FIELDS = {field.name for field in _FIELD_DEFS if isinstance(field.default, tuple)}
_BOOL_FIELDS = {field.name for field in _FIELD_DEFS if isinstance(field.default, bool)}


def _parse_simple_yaml_mapping(text: str) -> dict:
    """
    Minimal YAML parser for site config YAML files.

    Supports a subset of YAML used by this repo:
    - Top-level mapping of domain -> mapping
    - 2-space indented scalar fields and list fields
    - 4-space indented list items with "- <scalar>"
    - Scalars: strings (single/double quoted), booleans, null
    """

    def parse_scalar(token: str):
        token = token.strip()
        lowered = token.lower()
        if lowered in ("true", "yes", "on"):
            return True
        if lowered in ("false", "no", "off"):
            return False
        if lowered in ("null", "~", "none", ""):
            return None
        if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
            return token[1:-1].replace("''", "'")
        if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
            body = token[1:-1]
            try:
                return bytes(body, "utf-8").decode("unicode_escape")
            except Exception:
                return body
        return token

    root: dict = {}
    current_domain: str | None = None
    current_list_key: str | None = None
    current_list_indent: int | None = None

    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            if not stripped.endswith(":"):
                raise ValueError(f"Invalid YAML at line {lineno}: {line!r}")
            domain_token = stripped[:-1].strip()
            domain = parse_scalar(domain_token)
            if not isinstance(domain, str) or not domain:
                raise ValueError(f"Invalid domain key at line {lineno}: {domain_token!r}")
            root[domain] = {}
            current_domain = domain
            current_list_key = None
            current_list_indent = None
            continue

        if current_domain is None:
            raise ValueError(f"Unexpected indentation at line {lineno}: {line!r}")

        if stripped.startswith("- "):
            if not current_list_key or current_list_indent is None:
                raise ValueError(f"List item without list key at line {lineno}: {line!r}")
            if indent < current_list_indent:
                raise ValueError(f"Mis-indented list item at line {lineno}: {line!r}")
            value = parse_scalar(stripped[2:].strip())
            container = root[current_domain].get(current_list_key)
            if not isinstance(container, list):
                raise ValueError(
                    f"Expected list for {current_domain}.{current_list_key} at line {lineno}"
                )
            container.append(value)
            continue

        if indent == 2:
            if ":" not in stripped:
                raise ValueError(f"Invalid YAML mapping entry at line {lineno}: {line!r}")
            key, rest = stripped.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            if not key:
                raise ValueError(f"Empty key at line {lineno}: {line!r}")
            if rest == "":
                root[current_domain][key] = []
                current_list_key = key
                current_list_indent = indent
            else:
                root[current_domain][key] = parse_scalar(rest)
                current_list_key = None
                current_list_indent = None
            continue

        raise ValueError(f"Unsupported YAML syntax at line {lineno}: {line!r}")

    return root


def _load_yaml_text(raw_text: str) -> dict | None:
    if yaml is not None:
        return yaml.safe_load(raw_text)
    return _parse_simple_yaml_mapping(raw_text)


def _read_yaml_file(path: Path) -> dict | None:
    return _load_yaml_text(path.read_text(encoding="utf-8"))


def _load_article_site_config(
    path: Path = _SITE_CONFIG_PATH, directory: Path = _SITE_CONFIG_DIR
) -> Dict[str, ArticleSiteConfig]:
    raw: dict | None
    if directory.exists():
        files = sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml"))
        raw = {}
        for file_path in files:
            part = _read_yaml_file(file_path)
            if part is None:
                continue
            if not isinstance(part, dict):
                raise ValueError(f"Site config YAML must be a mapping in {file_path}.")
            for domain, values in part.items():
                if domain in raw:
                    raise ValueError(f"Duplicate site config for {domain} in {file_path}.")
                raw[domain] = values
    elif path.exists():
        raw = _read_yaml_file(path)
    else:
        raise FileNotFoundError(
            f"Site config YAML not found: {directory} or {path}"
        )
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Site config YAML must be a mapping of domain -> config.")

    configs: Dict[str, ArticleSiteConfig] = {}
    for domain, values in raw.items():
        if not isinstance(domain, str):
            raise ValueError("Site config domains must be strings.")
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ValueError(f"Config for {domain} must be a mapping.")

        unknown = set(values) - _ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"Unknown config keys for {domain}: {sorted(unknown)}")

        kwargs = {}
        for key, value in values.items():
            if key in _TUPLE_FIELDS:
                if value is None:
                    value = ()
                elif isinstance(value, str):
                    value = (value,)
                elif isinstance(value, list):
                    value = tuple(value)
                elif not isinstance(value, tuple):
                    raise TypeError(f"Config field {domain}.{key} must be a list of strings.")
            elif key in _BOOL_FIELDS and not isinstance(value, bool):
                raise TypeError(f"Config field {domain}.{key} must be a boolean.")
            kwargs[key] = value
        configs[domain] = ArticleSiteConfig(**kwargs)

    return configs


ARTICLE_SITE_CONFIG: Dict[str, ArticleSiteConfig] = _load_article_site_config()


def _matches_domain(domain: str, pattern: str) -> bool:
    if domain == pattern:
        return True
    return domain.endswith(f".{pattern}")


def get_article_site_config(domain: str) -> ArticleSiteConfig | None:
    """Return configuration overrides for the given domain, if any."""
    normalized = domain.lower()
    for pattern, config in ARTICLE_SITE_CONFIG.items():
        if _matches_domain(normalized, pattern):
            return config
    return None
