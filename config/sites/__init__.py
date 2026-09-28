from __future__ import annotations

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import Iterable

_LOADED = False


def _iter_site_modules() -> Iterable[str]:
    package_dir = Path(__file__).resolve().parent
    for module_info in iter_modules([str(package_dir)]):
        if module_info.ispkg:
            continue
        name = module_info.name
        if name.startswith("_"):
            continue
        yield name


def load_site_modules() -> None:
    """Import toàn bộ module site để register cấu hình."""
    global _LOADED
    if _LOADED:
        return
    for module_name in _iter_site_modules():
        import_module(f"{__name__}.{module_name}")
    _LOADED = True
