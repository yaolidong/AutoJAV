# AV Metadata Scraper - API Documentation

## Table of Contents

- [Overview](#overview)
- [Core Classes](#core-classes)
- [Data Models](#data-models)
- [Scrapers](#scrapers)
- [Utilities](#utilities)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

This document provides comprehensive API documentation for the AV Metadata Scraper project. The API is designed to be modular, extensible, and easy to integrate into other applications.

### Architecture Overview

```
AVMetadataScraper (Main Application)
├── FileScanner (File Discovery)
├── MetadataScraper (Data Extraction)
│   ├── JavDBScraper
│   ├── JavLibraryScraper
│   └── BaseScraper (Abstract)
├── FileOrganizer (File Management)
├── ImageDownloader (Image Processing)
└── ConfigManager (Configuration)
```

## Core Classes

### AVMetadataScraper

Main application class that orchestrates the entire scraping and organization process.

```python
class AVMetadataScraper:
    """Main application class for AV metadata scraping and file organization."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the AV Metadata Scraper.
        
        Args:
            config_path: Path to configuration file (optional)
        """
    
    async def start(self) -> None:
        """Start the scraping process."""
    
    async def stop(self) -> None:
        """Stop the scraping process gracefully."""
    
    async def process_files(self, 
                          source_dir: Optional[Path] = None,
                          target_dir: Optional[Path] = None,
                          resume: bool = False) -> ProcessingResult:
        """
        Process video files in the source directory.
        
        Args:
            source_dir: Source directory to scan (optional, uses config default)
            target_dir: Target directory for organized files (optional)
            resume: Resume from previous interrupted session
            
        Returns:
            ProcessingResult with statistics and status
        """
    
    async def scan_directory(self, directory: Path) -> List[VideoFile]:
        """
        Scan directory for video files.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of discovered video files
        """
    
    def get_status(self) -> ApplicationStatus:
        """Get current application status and statistics."""
    
    @property
    def is_running(self) -> bool:
        """Check if the application is currently running."""
```

### FileScanner

Handles discovery and analysis of video files.

```python
class FileScanner:
    """Scans directories for video files and extracts basic information."""
    
    def __init__(self, supported_extensions: List[str]):
        """
        Initialize the file scanner.
        
        Args:
            supported_extensions: List of supported video file extensions
        """
    
    async def scan_directory(self, 
                           directory: Path, 
                           recursive: bool = True) -> List[VideoFile]:
        """
        Scan directory for video files.
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of discovered video files
        """
    
    def extract_code_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract video code from filename using pattern matching.
        
        Args:
            filename: Video filename
            
        Returns:
            Extracted video code or None if not found
        """
    
    def is_video_file(self, file_path: Path) -> bool:
        """
        Check if file is a supported video format.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is a supported video format
        """
    
    def get_file_info(self, file_path: Path) -> VideoFile:
        """
        Get detailed information about a video file.
        
        Args:
            file_path: Path to video file
            
        Returns:
            VideoFile object with file information
        """
```

### MetadataScraper

Coordinates metadata scraping from multiple sources.

```python
class MetadataScraper:
    """Coordinates metadata scraping from multiple sources."""
    
    def __init__(self, scrapers: List[BaseScraper], config: Config):
        """
        Initialize the metadata scraper.
        
        Args:
            scrapers: List of scraper instances
            config: Application configuration
        """
    
    async def scrape_metadata(self, video_code: str) -> Optional[MovieMetadata]:
        """
        Scrape metadata for a video code from available sources.
        
        Args:
            video_code: Video identification code
            
        Returns:
            MovieMetadata object or None if not found
        """
    
    async def scrape_with_priority(self, 
                                 video_code: str,
                                 priority_order: List[str]) -> Optional[MovieMetadata]:
        """
        Scrape metadata using specified scraper priority.
        
        Args:
            video_code: Video identification code
            priority_order: List of scraper names in priority order
            
        Returns:
            MovieMetadata object or None if not found
        """
    
    def get_available_scrapers(self) -> List[str]:
        """Get list of available scraper names."""
    
    async def test_scrapers(self) -> Dict[str, bool]:
        """Test connectivity and functionality of all scrapers."""
```

### FileOrganizer

Handles file organization and metadata saving.

```python
class FileOrganizer:
    """Organizes video files based on metadata."""
    
    def __init__(self, target_directory: Path, naming_pattern: str, config: Config):
        """
        Initialize the file organizer.
        
        Args:
            target_directory: Base directory for organized files
            naming_pattern: Pattern for file/directory naming
            config: Application configuration
        """
    
    async def organize_file(self, 
                          video_file: VideoFile, 
                          metadata: MovieMetadata) -> OrganizationResult:
        """
        Organize a video file based on its metadata.
        
        Args:
            video_file: Video file to organize
            metadata: Associated metadata
            
        Returns:
            OrganizationResult with operation details
        """
    
    def generate_target_path(self, 
                           metadata: MovieMetadata, 
                           file_extension: str) -> Path:
        """
        Generate target file path based on naming pattern.
        
        Args:
            metadata: Movie metadata
            file_extension: Original file extension
            
        Returns:
            Generated target path
        """
    
    async def save_metadata(self, 
                          metadata: MovieMetadata, 
                          target_directory: Path) -> Path:
        """
        Save metadata to JSON file.
        
        Args:
            metadata: Metadata to save
            target_directory: Directory to save metadata file
            
        Returns:
            Path to saved metadata file
        """
    
    def create_directory_structure(self, path: Path) -> None:
        """
        Create directory structure for target path.
        
        Args:
            path: Target path requiring directory structure
        """
    
    async def move_file(self, source: Path, target: Path, safe_mode: bool = True) -> bool:
        """
        Move or copy file from source to target.
        
        Args:
            source: Source file path
            target: Target file path
            safe_mode: If True, copy instead of move
            
        Returns:
            True if operation successful
        """
```

## Data Models

### VideoFile

Represents a video file with its properties.

```python
@dataclass
class VideoFile:
    """Represents a video file with its properties."""
    
    file_path: Path
    filename: str
    file_size: int
    extension: str
    detected_code: Optional[str] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    
    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    @property
    def size_gb(self) -> float:
        """File size in gigabytes."""
        return self.file_size / (1024 * 1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
    
    @classmethod
    def from_path(cls, file_path: Path) -> 'VideoFile':
        """Create VideoFile instance from file path."""
```

### MovieMetadata

Represents scraped metadata for a movie.

```python
@dataclass
class MovieMetadata:
    """Represents movie metadata scraped from various sources."""
    
    code: str
    title: str
    title_en: Optional[str] = None
    actresses: List[str] = field(default_factory=list)
    release_date: Optional[date] = None
    duration: Optional[int] = None
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
    
    @property
    def primary_actress(self) -> Optional[str]:
        """Get primary (first) actress name."""
        return self.actresses[0] if self.actresses else None
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Duration in minutes."""
        return self.duration
    
    @property
    def duration_formatted(self) -> Optional[str]:
        """Formatted duration string (e.g., '2h 30m')."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MovieMetadata':
        """Create MovieMetadata instance from dictionary."""
    
    def merge_with(self, other: 'MovieMetadata') -> 'MovieMetadata':
        """Merge with another metadata object, preferring non-empty values."""
```

### Config

Application configuration model.

```python
@dataclass
class Config:
    """Application configuration model."""
    
    # Directory configuration
    source_directory: Path
    target_directory: Path
    
    # Login configuration
    javdb_username: Optional[str] = None
    javdb_password: Optional[str] = None
    
    # Scraping configuration
    scraper_priority: List[str] = field(default_factory=lambda: ['javdb', 'javlibrary'])
    max_concurrent_files: int = 3
    max_concurrent_requests: int = 2
    max_concurrent_downloads: int = 4
    retry_attempts: int = 3
    request_timeout: int = 30
    
    # File naming configuration
    naming_pattern: str = "{actress}/{code}/{code}.{ext}"
    
    # Browser configuration
    headless_browser: bool = True
    browser_timeout: int = 30
    
    # Network configuration
    proxy_url: Optional[str] = None
    
    # Feature configuration
    download_images: bool = True
    save_metadata: bool = True
    safe_mode: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    
    # Supported extensions
    supported_extensions: List[str] = field(default_factory=lambda: [
        '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v', '.ts', '.m2ts'
    ])
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'Config':
        """Load configuration from YAML file."""
    
    def to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
```

## Scrapers

### BaseScraper

Abstract base class for all scrapers.

```python
class BaseScraper(ABC):
    """Abstract base class for metadata scrapers."""
    
    def __init__(self, config: Config):
        """
        Initialize the scraper.
        
        Args:
            config: Application configuration
        """
    
    @abstractmethod
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """
        Search for movie metadata by code.
        
        Args:
            code: Video identification code
            
        Returns:
            MovieMetadata object or None if not found
        """
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the scraper is available and functional.
        
        Returns:
            True if scraper is available
        """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Scraper name identifier."""
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the scraped website."""
    
    async def test_connection(self) -> bool:
        """Test connection to the scraped website."""
    
    def _normalize_code(self, code: str) -> str:
        """Normalize video code format."""
    
    def _extract_actresses(self, html_content: str) -> List[str]:
        """Extract actress names from HTML content."""
    
    def _extract_genres(self, html_content: str) -> List[str]:
        """Extract genre information from HTML content."""
```

### JavDBScraper

Scraper implementation for JavDB website.

```python
class JavDBScraper(BaseScraper):
    """Scraper for JavDB website."""
    
    def __init__(self, config: Config, login_manager: LoginManager):
        """
        Initialize JavDB scraper.
        
        Args:
            config: Application configuration
            login_manager: Login manager instance
        """
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """Search for movie on JavDB."""
    
    async def is_available(self) -> bool:
        """Check JavDB availability."""
    
    async def login_if_needed(self) -> bool:
        """Login to JavDB if credentials are provided."""
    
    def _parse_movie_page(self, html_content: str, movie_url: str) -> MovieMetadata:
        """Parse movie details from JavDB movie page."""
    
    def _extract_cover_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract cover image URL from page."""
    
    def _extract_movie_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract basic movie information from page."""
```

### JavLibraryScraper

Scraper implementation for JavLibrary website.

```python
class JavLibraryScraper(BaseScraper):
    """Scraper for JavLibrary website."""
    
    def __init__(self, config: Config):
        """
        Initialize JavLibrary scraper.
        
        Args:
            config: Application configuration
        """
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """Search for movie on JavLibrary."""
    
    async def is_available(self) -> bool:
        """Check JavLibrary availability."""
    
    def _parse_search_results(self, html_content: str) -> List[str]:
        """Parse search results to get movie URLs."""
    
    def _parse_movie_page(self, html_content: str, movie_url: str) -> MovieMetadata:
        """Parse movie details from JavLibrary movie page."""
```

## Utilities

### LoginManager

Handles website login and session management.

```python
class LoginManager:
    """Manages website login and session persistence."""
    
    def __init__(self, username: str, password: str, driver: WebDriver):
        """
        Initialize login manager.
        
        Args:
            username: Login username
            password: Login password
            driver: WebDriver instance
        """
    
    async def login(self, login_url: str) -> bool:
        """
        Perform login to website.
        
        Args:
            login_url: URL of login page
            
        Returns:
            True if login successful
        """
    
    async def is_logged_in(self, check_url: str) -> bool:
        """
        Check if currently logged in.
        
        Args:
            check_url: URL to check login status
            
        Returns:
            True if logged in
        """
    
    async def refresh_session(self) -> bool:
        """Refresh login session."""
    
    def save_cookies(self, file_path: Path) -> None:
        """Save cookies to file."""
    
    def load_cookies(self, file_path: Path) -> bool:
        """Load cookies from file."""
    
    async def handle_captcha(self) -> bool:
        """Handle captcha if present."""
```

### ImageDownloader

Handles downloading and processing of images.

```python
class ImageDownloader:
    """Downloads and processes images (covers, posters, screenshots)."""
    
    def __init__(self, config: Config):
        """
        Initialize image downloader.
        
        Args:
            config: Application configuration
        """
    
    async def download_image(self, 
                           url: str, 
                           target_path: Path,
                           resize: Optional[Tuple[int, int]] = None) -> bool:
        """
        Download image from URL.
        
        Args:
            url: Image URL
            target_path: Target file path
            resize: Optional resize dimensions (width, height)
            
        Returns:
            True if download successful
        """
    
    async def download_movie_images(self, 
                                  metadata: MovieMetadata, 
                                  target_directory: Path) -> List[Path]:
        """
        Download all images for a movie.
        
        Args:
            metadata: Movie metadata containing image URLs
            target_directory: Directory to save images
            
        Returns:
            List of downloaded image paths
        """
    
    def create_thumbnail(self, 
                        source_path: Path, 
                        target_path: Path, 
                        size: Tuple[int, int] = (300, 200)) -> bool:
        """
        Create thumbnail from image.
        
        Args:
            source_path: Source image path
            target_path: Target thumbnail path
            size: Thumbnail dimensions
            
        Returns:
            True if thumbnail created successfully
        """
    
    def optimize_image(self, 
                      image_path: Path, 
                      quality: int = 85,
                      max_size: Optional[Tuple[int, int]] = None) -> bool:
        """
        Optimize image file size and quality.
        
        Args:
            image_path: Path to image file
            quality: JPEG quality (1-100)
            max_size: Maximum dimensions (width, height)
            
        Returns:
            True if optimization successful
        """
```

### ProgressTracker

Tracks and persists processing progress.

```python
class ProgressTracker:
    """Tracks processing progress and enables resume functionality."""
    
    def __init__(self, session_id: str, persistence_file: Path):
        """
        Initialize progress tracker.
        
        Args:
            session_id: Unique session identifier
            persistence_file: File to save progress data
        """
    
    def start_session(self, total_files: int) -> None:
        """
        Start new processing session.
        
        Args:
            total_files: Total number of files to process
        """
    
    def update_progress(self, 
                       file_path: Path, 
                       status: str, 
                       metadata: Optional[Dict] = None) -> None:
        """
        Update progress for a file.
        
        Args:
            file_path: Path of processed file
            status: Processing status
            metadata: Optional metadata about processing
        """
    
    def get_progress(self) -> ProgressInfo:
        """Get current progress information."""
    
    def save_progress(self) -> None:
        """Save progress to persistence file."""
    
    def load_progress(self) -> bool:
        """Load progress from persistence file."""
    
    def get_unprocessed_files(self, all_files: List[Path]) -> List[Path]:
        """Get list of files that haven't been processed yet."""
    
    def is_file_processed(self, file_path: Path) -> bool:
        """Check if file has been processed."""
```

## Configuration

### ConfigManager

Manages application configuration.

```python
class ConfigManager:
    """Manages application configuration loading and validation."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
    
    def load_config(self) -> Config:
        """
        Load configuration from file and environment variables.
        
        Returns:
            Loaded configuration object
        """
    
    def save_config(self, config: Config) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration object to save
        """
    
    def validate_config(self, config: Config) -> List[str]:
        """
        Validate configuration and return errors.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
    
    def get_default_config(self) -> Config:
        """Get default configuration."""
    
    def merge_env_variables(self, config: Config) -> Config:
        """Merge environment variables into configuration."""
```

## Error Handling

### Custom Exceptions

```python
class AVScraperError(Exception):
    """Base exception for AV Scraper errors."""
    pass

class ConfigurationError(AVScraperError):
    """Configuration-related errors."""
    pass

class ScrapingError(AVScraperError):
    """Scraping-related errors."""
    pass

class NetworkError(AVScraperError):
    """Network-related errors."""
    pass

class FileOperationError(AVScraperError):
    """File operation errors."""
    pass

class LoginError(AVScraperError):
    """Login-related errors."""
    pass
```

### ErrorHandler

Centralized error handling and recovery.

```python
class ErrorHandler:
    """Centralized error handling and recovery mechanisms."""
    
    def __init__(self, config: Config):
        """
        Initialize error handler.
        
        Args:
            config: Application configuration
        """
    
    async def handle_scraping_error(self, 
                                  error: Exception, 
                                  context: Dict[str, Any]) -> bool:
        """
        Handle scraping errors with retry logic.
        
        Args:
            error: Exception that occurred
            context: Context information about the error
            
        Returns:
            True if error was handled and operation should retry
        """
    
    async def handle_network_error(self, 
                                 error: Exception, 
                                 retry_count: int) -> bool:
        """
        Handle network errors with exponential backoff.
        
        Args:
            error: Network exception
            retry_count: Current retry attempt
            
        Returns:
            True if should retry
        """
    
    def handle_file_error(self, 
                         error: Exception, 
                         file_path: Path) -> None:
        """
        Handle file operation errors.
        
        Args:
            error: File operation exception
            file_path: Path of file that caused error
        """
    
    def should_retry(self, 
                    error: Exception, 
                    retry_count: int, 
                    max_retries: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            error: Exception that occurred
            retry_count: Current retry count
            max_retries: Maximum allowed retries
            
        Returns:
            True if should retry
        """
```

## Examples

### Basic Usage

```python
from pathlib import Path
from src.main_application import AVMetadataScraper

# Initialize with default configuration
scraper = AVMetadataScraper()

# Start processing
await scraper.start()

# Process files
result = await scraper.process_files(
    source_dir=Path("/path/to/videos"),
    target_dir=Path("/path/to/organized")
)

print(f"Processed {result.processed_count} files")
print(f"Errors: {result.error_count}")

# Stop gracefully
await scraper.stop()
```

### Custom Configuration

```python
from pathlib import Path
from src.models.config import Config
from src.main_application import AVMetadataScraper

# Create custom configuration
config = Config(
    source_directory=Path("/videos"),
    target_directory=Path("/organized"),
    javdb_username="your_username",
    javdb_password="your_password",
    max_concurrent_files=2,
    naming_pattern="{studio}/{actress}/{code}.{ext}"
)

# Initialize with custom config
scraper = AVMetadataScraper()
scraper.config = config

# Process files
await scraper.start()
result = await scraper.process_files()
```

### Using Individual Components

```python
from pathlib import Path
from src.scanner.file_scanner import FileScanner
from src.scrapers.metadata_scraper import MetadataScraper
from src.scrapers.javdb_scraper import JavDBScraper
from src.models.config import Config

# Initialize components
config = Config.from_file(Path("config.yaml"))
scanner = FileScanner(config.supported_extensions)
scrapers = [JavDBScraper(config)]
metadata_scraper = MetadataScraper(scrapers, config)

# Scan for files
video_files = await scanner.scan_directory(Path("/videos"))

# Scrape metadata for each file
for video_file in video_files:
    if video_file.detected_code:
        metadata = await metadata_scraper.scrape_metadata(video_file.detected_code)
        if metadata:
            print(f"Found metadata for {video_file.filename}: {metadata.title}")
```

### Error Handling Example

```python
from src.main_application import AVMetadataScraper
from src.utils.error_handler import AVScraperError, NetworkError

try:
    scraper = AVMetadataScraper()
    await scraper.start()
    result = await scraper.process_files()
    
except NetworkError as e:
    print(f"Network error: {e}")
    # Handle network-specific errors
    
except AVScraperError as e:
    print(f"Application error: {e}")
    # Handle application-specific errors
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle unexpected errors
    
finally:
    if scraper and scraper.is_running:
        await scraper.stop()
```

### Custom Scraper Implementation

```python
from src.scrapers.base_scraper import BaseScraper
from src.models.movie_metadata import MovieMetadata
from typing import Optional

class CustomScraper(BaseScraper):
    """Custom scraper implementation."""
    
    @property
    def name(self) -> str:
        return "custom"
    
    @property
    def base_url(self) -> str:
        return "https://example.com"
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """Implement custom scraping logic."""
        # Your custom scraping implementation
        pass
    
    async def is_available(self) -> bool:
        """Check if custom site is available."""
        try:
            # Test connection to your site
            return True
        except:
            return False

# Register custom scraper
from src.scrapers.metadata_scraper import MetadataScraper

custom_scraper = CustomScraper(config)
scrapers = [custom_scraper]
metadata_scraper = MetadataScraper(scrapers, config)
```

---

For more information, see:
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)