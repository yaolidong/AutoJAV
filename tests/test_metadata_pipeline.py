import asyncio
from typing import Optional

from src.models.movie_metadata import MovieMetadata
from src.scrapers.base_scraper import BaseScraper
from src.scrapers.metadata_scraper import MetadataScraper


class FakeScraper(BaseScraper):
    def __init__(self, name: str, metadata: Optional[MovieMetadata], delay: float = 0.0):
        super().__init__(name)
        self._metadata = metadata
        self._delay = delay

    async def search_movie(self, code: str):
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._metadata

    async def is_available(self) -> bool:
        return True


def test_metadata_scraper_merges_sources():
    metadata_a = MovieMetadata(
        code="ABC-001",
        title="ABC-001",
        actresses=["Alice"],
        studio="StudioA",
        cover_url="https://example.com/a.jpg",
    )
    metadata_b = MovieMetadata(
        code="ABC-001",
        title="ABC-001 A New Beginning",
        actresses=["Alice", "Bella"],
        genres=["Drama"],
        description="An extended synopsis",
        poster_url="https://example.com/b.jpg",
    )

    scraper = MetadataScraper(
        scrapers=[
            FakeScraper("SourceA", metadata_a, delay=0.05),
            FakeScraper("SourceB", metadata_b, delay=0.01),
        ],
        max_concurrent_requests=2,
        timeout_seconds=2,
        retry_attempts=0,
        cache_duration_minutes=1,
    )

    result = asyncio.run(scraper.scrape_metadata("ABC-001"))

    assert result is not None
    assert result.title == "ABC-001 A New Beginning"
    assert set(result.actresses) == {"Alice", "Bella"}
    assert result.cover_url == "https://example.com/a.jpg"
    assert result.poster_url == "https://example.com/b.jpg"
    assert "SourceA" in result.source_urls
    assert "SourceB" in result.source_urls
    assert result.extra.get("source_scores")


def test_metadata_scraper_uses_cache():
    metadata = MovieMetadata(
        code="XYZ-999",
        title="XYZ-999",
        actresses=["Kana"],
    )

    scraper = MetadataScraper(
        scrapers=[FakeScraper("CacheSource", metadata)],
        max_concurrent_requests=1,
        timeout_seconds=2,
        retry_attempts=0,
        cache_duration_minutes=5,
    )

    first = asyncio.run(scraper.scrape_metadata("XYZ-999"))
    second = asyncio.run(scraper.scrape_metadata("XYZ-999"))

    assert first is not None and second is not None
    assert scraper.stats["cache_hits"] == 1

