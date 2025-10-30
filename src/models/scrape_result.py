"""Data structures for scraper orchestration."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from .movie_metadata import MovieMetadata


@dataclass
class ScrapeResult:
    """Container describing a single scraper attempt."""

    source: str
    metadata: Optional[MovieMetadata]
    success: bool
    score: float
    latency: Optional[timedelta] = None
    error: Optional[str] = None

    @property
    def has_metadata(self) -> bool:
        """Returns True when the scraper yielded usable metadata."""
        return self.success and self.metadata is not None

