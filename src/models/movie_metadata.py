"""Movie metadata data model."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional


@dataclass
class MovieMetadata:
    """Represents metadata for a movie/video."""

    code: str
    title: str
    title_en: Optional[str] = None
    description: Optional[str] = None
    actresses: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    release_date: Optional[date] = None
    duration: Optional[int] = None  # in minutes
    studio: Optional[str] = None
    label: Optional[str] = None
    director: Optional[str] = None
    series: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    rating: Optional[float] = None
    rating_votes: Optional[int] = None
    cover_url: Optional[str] = None
    poster_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    sample_clips: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    source_urls: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate and normalize the metadata after initialization."""
        if not self.code:
            raise ValueError("code cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")
        if self.rating is not None and not (0 <= self.rating <= 10):
            raise ValueError("rating must be between 0 and 10")
        if self.duration is not None and self.duration < 0:
            raise ValueError("duration cannot be negative")

        self.actresses = self._normalize_list(self.actresses)
        self.aliases = self._normalize_list(self.aliases)
        self.genres = self._normalize_list(self.genres)
        self.screenshots = self._normalize_list(self.screenshots)
        self.sample_clips = self._normalize_list(self.sample_clips)

        if self.source_url and "primary" not in self.source_urls:
            self.source_urls.setdefault("primary", self.source_url)
        elif not self.source_url and self.source_urls:
            # Promote the first source into legacy field for backward compatibility
            self.source_url = next(iter(self.source_urls.values()))

    @staticmethod
    def _normalize_list(values: List[str]) -> List[str]:
        """Strip whitespace and remove duplicates while preserving order."""
        seen = set()
        normalized: List[str] = []
        for value in values:
            if not value:
                continue
            cleaned = value.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)
        return normalized

    @staticmethod
    def _prefer_text(primary: Optional[str], secondary: Optional[str]) -> Optional[str]:
        """Choose the more informative text based on length."""
        if primary and secondary:
            return primary if len(primary) >= len(secondary) else secondary
        return primary or secondary

    @staticmethod
    def _prefer_numeric(
        primary: Optional[int], secondary: Optional[int], *, prefer_max: bool = True
    ) -> Optional[int]:
        if primary is None:
            return secondary
        if secondary is None:
            return primary
        return max(primary, secondary) if prefer_max else min(primary, secondary)

    @staticmethod
    def _prefer_date(primary: Optional[date], secondary: Optional[date]) -> Optional[date]:
        if primary and secondary:
            return min(primary, secondary)
        return primary or secondary

    @staticmethod
    def _prefer_rating(primary: Optional[float], secondary: Optional[float]) -> Optional[float]:
        if primary is None:
            return secondary
        if secondary is None:
            return primary
        return max(primary, secondary)

    @staticmethod
    def _merge_lists(left: List[str], right: List[str]) -> List[str]:
        merged = list(left)
        seen = set(left)
        for item in right:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)
        return merged

    def merge_with(self, other: "MovieMetadata") -> "MovieMetadata":
        """Merge two metadata objects, preferring richer information."""
        if self.code != other.code:
            raise ValueError("Cannot merge metadata for different codes")

        merged = MovieMetadata(
            code=self.code,
            title=self._prefer_text(self.title, other.title) or self.code,
            title_en=self._prefer_text(self.title_en, other.title_en),
            description=self._prefer_text(self.description, other.description),
            actresses=self._merge_lists(self.actresses, other.actresses),
            aliases=self._merge_lists(self.aliases, other.aliases),
            release_date=self._prefer_date(self.release_date, other.release_date),
            duration=self._prefer_numeric(self.duration, other.duration, prefer_max=True),
            studio=self._prefer_text(self.studio, other.studio),
            label=self._prefer_text(self.label, other.label),
            director=self._prefer_text(self.director, other.director),
            series=self._prefer_text(self.series, other.series),
            genres=self._merge_lists(self.genres, other.genres),
            rating=self._prefer_rating(self.rating, other.rating),
            rating_votes=self._prefer_numeric(self.rating_votes, other.rating_votes, prefer_max=True),
            cover_url=self._prefer_text(self.cover_url, other.cover_url),
            poster_url=self._prefer_text(self.poster_url, other.poster_url),
            thumbnail_url=self._prefer_text(self.thumbnail_url, other.thumbnail_url),
            screenshots=self._merge_lists(self.screenshots, other.screenshots),
            sample_clips=self._merge_lists(self.sample_clips, other.sample_clips),
            source_url=self.source_url or other.source_url,
            source_urls={**other.source_urls, **self.source_urls},
            extra={**other.extra, **self.extra},
            scraped_at=max(self.scraped_at, other.scraped_at),
        )

        if not merged.source_url and merged.source_urls:
            merged.source_url = next(iter(merged.source_urls.values()))

        return merged

    @property
    def primary_actress(self) -> Optional[str]:
        """Get the primary (first) actress."""
        return self.actresses[0] if self.actresses else None

    @property
    def duration_str(self) -> str:
        """Get duration as formatted string."""
        if self.duration is None:
            return "Unknown"
        hours = self.duration // 60
        minutes = self.duration % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def add_source(self, source_name: str, url: Optional[str]) -> None:
        """Register an additional source URL."""
        if source_name:
            if url:
                self.source_urls[source_name] = url
                if not self.source_url:
                    self.source_url = url
            else:
                self.source_urls.setdefault(source_name, "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code,
            "title": self.title,
            "title_en": self.title_en,
            "description": self.description,
            "actresses": self.actresses,
            "aliases": self.aliases,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "duration": self.duration,
            "studio": self.studio,
            "label": self.label,
            "director": self.director,
            "series": self.series,
            "genres": self.genres,
            "rating": self.rating,
            "rating_votes": self.rating_votes,
            "cover_url": self.cover_url,
            "poster_url": self.poster_url,
            "thumbnail_url": self.thumbnail_url,
            "screenshots": self.screenshots,
            "sample_clips": self.sample_clips,
            "source_url": self.source_url,
            "source_urls": self.source_urls,
            "extra": self.extra,
            "scraped_at": self.scraped_at.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of the metadata."""
        actress_str = f" - {self.primary_actress}" if self.primary_actress else ""
        return f"MovieMetadata(code='{self.code}', title='{self.title}'{actress_str})"