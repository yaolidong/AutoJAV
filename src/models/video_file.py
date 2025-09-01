"""Video file data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class VideoFile:
    """Represents a video file with its metadata."""
    
    file_path: str
    filename: str
    file_size: int
    extension: str
    detected_code: Optional[str] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate the video file data after initialization."""
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if not self.filename:
            raise ValueError("filename cannot be empty")
        if self.file_size < 0:
            raise ValueError("file_size cannot be negative")
        if not self.extension:
            raise ValueError("extension cannot be empty")
    
    @property
    def full_path(self) -> str:
        """Get the full file path."""
        return self.file_path
    
    @property
    def size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size / (1024 * 1024)
    
    def __str__(self) -> str:
        """String representation of the video file."""
        return f"VideoFile(filename='{self.filename}', size={self.size_mb:.1f}MB, code='{self.detected_code}')"