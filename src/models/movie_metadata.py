"""Movie metadata data model."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional


@dataclass
class MovieMetadata:
    """Represents metadata for a movie/video."""
    
    code: str
    title: str
    title_en: Optional[str] = None
    actresses: List[str] = field(default_factory=list)
    release_date: Optional[date] = None
    duration: Optional[int] = None  # in minutes
    studio: Optional[str] = None
    series: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    cover_url: Optional[str] = None
    poster_url: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    description: Optional[str] = None
    rating: Optional[float] = None
    source_url: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate the metadata after initialization."""
        if not self.code:
            raise ValueError("code cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")
        if self.rating is not None and not (0 <= self.rating <= 10):
            raise ValueError("rating must be between 0 and 10")
        if self.duration is not None and self.duration < 0:
            raise ValueError("duration cannot be negative")
    
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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'code': self.code,
            'title': self.title,
            'title_en': self.title_en,
            'actresses': self.actresses,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'duration': self.duration,
            'studio': self.studio,
            'series': self.series,
            'genres': self.genres,
            'cover_url': self.cover_url,
            'poster_url': self.poster_url,
            'screenshots': self.screenshots,
            'description': self.description,
            'rating': self.rating,
            'source_url': self.source_url,
            'scraped_at': self.scraped_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of the metadata."""
        actress_str = f" - {self.primary_actress}" if self.primary_actress else ""
        return f"MovieMetadata(code='{self.code}', title='{self.title}'{actress_str})"