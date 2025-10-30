"""Scrapers package with lazy exports to keep optional deps optional."""

from importlib import import_module
from typing import Any, Dict, Tuple

_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    "BaseScraper": (".base_scraper", "BaseScraper"),
    "JavDBScraper": (".javdb_scraper", "JavDBScraper"),
    "JavLibraryScraper": (".javlibrary_scraper", "JavLibraryScraper"),
    "MetadataScraper": (".metadata_scraper", "MetadataScraper"),
    "ScraperFactory": (".scraper_factory", "ScraperFactory"),
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name in _EXPORT_MAP:
        module_name, attr = _EXPORT_MAP[name]
        module = import_module(module_name, package=__name__)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")