"""Parallel metadata scraper wrapper built on top of MetadataScraper."""

import logging
from typing import List, Optional

from ..models.movie_metadata import MovieMetadata
from .base_scraper import BaseScraper
from .metadata_scraper import MetadataScraper


class ParallelMetadataScraper:
    """Convenience facade that runs all scrapers in parallel."""

    def __init__(
        self,
        scrapers: List[BaseScraper],
        cache_duration_minutes: int = 60,
        parallel_timeout: int = 30
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            "Initializing ParallelMetadataScraper with %d scrapers", len(scrapers)
        )

        self._metadata_scraper = MetadataScraper(
            scrapers=scrapers,
            max_concurrent_requests=max(1, len(scrapers)),
            timeout_seconds=parallel_timeout,
            retry_attempts=2,
            cache_duration_minutes=cache_duration_minutes,
        )

    async def scrape_metadata_parallel(
        self, code: str, preferred_scrapers: Optional[List[str]] = None
    ) -> Optional[MovieMetadata]:
        """Delegate to the underlying MetadataScraper."""
        return await self._metadata_scraper.scrape_metadata(code, preferred_scrapers)

    async def scrape_metadata(self, code: str) -> Optional[MovieMetadata]:
        """Alias for backward compatibility."""
        return await self.scrape_metadata_parallel(code)

    def get_stats(self):
        """Expose the inner scraper statistics."""
        return self._metadata_scraper.get_scraper_stats()

    def clear_cache(self) -> None:
        """Clear cached results."""
        self._metadata_scraper.clear_cache()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self._metadata_scraper.cleanup()