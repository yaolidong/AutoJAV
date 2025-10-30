"""Package entry point with lazy imports to avoid heavy dependencies at import time."""

from importlib import import_module
from typing import Any, Dict, Tuple

__version__ = "1.0.0"
__author__ = "AV Metadata Scraper Team"
__description__ = "Automated video metadata scraping and organizing system"

_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    # Main application
    "AVMetadataScraper": (".main_application", "AVMetadataScraper"),

    # Core models
    "VideoFile": (".models.video_file", "VideoFile"),
    "MovieMetadata": (".models.movie_metadata", "MovieMetadata"),
    "Config": (".models.config", "Config"),

    # Main components
    "FileScanner": (".scanner.file_scanner", "FileScanner"),
    "FileOrganizer": (".organizers.file_organizer", "FileOrganizer"),
    "ImageDownloader": (".downloaders.image_downloader", "ImageDownloader"),
    "MetadataScraper": (".scrapers.metadata_scraper", "MetadataScraper"),
    "ScraperFactory": (".scrapers.scraper_factory", "ScraperFactory"),

    # Configuration
    "ConfigManager": (".config.config_manager", "ConfigManager"),

    # CLI
    "cli_main": (".cli.cli_main", "main"),
    "AVScraperCLI": (".cli.AVScraperCLI", "AVScraperCLI"),
}

__all__ = [
    "__version__",
    "__author__",
    "__description__",
    *list(_EXPORT_MAP.keys()),
]


def __getattr__(name: str) -> Any:  # pragma: no cover - trivial getter
    if name in _EXPORT_MAP:
        module_name, attribute_name = _EXPORT_MAP[name]
        module = import_module(module_name, package=__name__)
        value = getattr(module, attribute_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")