"""Scraping history data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class ProcessStatus(Enum):
    """Processing status enumeration."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class ScrapeHistoryEntry:
    """Represents a single scraping history entry."""
    
    # File information
    original_filename: str
    original_path: str
    file_size: int  # in bytes
    file_extension: str
    
    # Processing information
    detected_code: Optional[str]
    process_time: datetime
    status: ProcessStatus
    
    # Result information
    new_filename: Optional[str] = None
    new_path: Optional[str] = None
    organized_path: Optional[str] = None
    
    # Metadata information
    metadata_found: bool = False
    title: Optional[str] = None
    actresses: List[str] = field(default_factory=list)
    studio: Optional[str] = None
    release_date: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    cover_downloaded: bool = False
    
    # Scraper information
    scraper_used: Optional[str] = None
    scraping_time: Optional[float] = None  # in seconds
    
    # Error information
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    
    # Additional metadata
    metadata_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate the history entry after initialization."""
        if not self.original_filename:
            raise ValueError("original_filename cannot be empty")
        if not self.original_path:
            raise ValueError("original_path cannot be empty")
        if self.file_size < 0:
            raise ValueError("file_size cannot be negative")
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size / (1024 * 1024)
    
    @property
    def is_successful(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessStatus.SUCCESS
    
    @property
    def has_metadata(self) -> bool:
        """Check if metadata was found."""
        return self.metadata_found and (self.title or self.actresses)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'original_filename': self.original_filename,
            'original_path': self.original_path,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'file_extension': self.file_extension,
            'detected_code': self.detected_code,
            'process_time': self.process_time.isoformat() if self.process_time else None,
            'status': self.status.value if self.status else None,
            'new_filename': self.new_filename,
            'new_path': self.new_path,
            'organized_path': self.organized_path,
            'metadata_found': self.metadata_found,
            'title': self.title,
            'actresses': self.actresses,
            'studio': self.studio,
            'release_date': self.release_date,
            'genres': self.genres,
            'cover_downloaded': self.cover_downloaded,
            'scraper_used': self.scraper_used,
            'scraping_time': self.scraping_time,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'metadata_json': self.metadata_json,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapeHistoryEntry':
        """Create instance from dictionary."""
        # Handle process_time conversion
        if 'process_time' in data and data['process_time']:
            if isinstance(data['process_time'], str):
                data['process_time'] = datetime.fromisoformat(data['process_time'])
        else:
            data['process_time'] = datetime.now()
        
        # Handle status conversion
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ProcessStatus(data['status'])
        
        # Remove calculated properties if present
        data.pop('file_size_mb', None)
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation."""
        status_emoji = {
            ProcessStatus.SUCCESS: "✅",
            ProcessStatus.FAILED: "❌",
            ProcessStatus.PARTIAL: "⚠️",
            ProcessStatus.SKIPPED: "⏭️"
        }
        
        emoji = status_emoji.get(self.status, "❓")
        return f"{emoji} {self.original_filename} → {self.new_filename or 'N/A'} [{self.status.value}]"