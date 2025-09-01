"""Configuration data model."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Configuration settings for the AV metadata scraper."""
    
    # Directory configuration
    source_directory: str
    target_directory: str
    
    # Login configuration
    javdb_username: Optional[str] = None
    javdb_password: Optional[str] = None
    
    # Scraping configuration
    scraper_priority: List[str] = field(default_factory=lambda: ['javdb', 'javlibrary'])
    max_concurrent_files: int = 3
    retry_attempts: int = 3
    
    # File naming configuration
    naming_pattern: str = "{actress}/{code}/{code}.{ext}"
    
    # Browser configuration
    headless_browser: bool = True
    browser_timeout: int = 30
    
    # Proxy configuration
    proxy_url: Optional[str] = None
    
    # Other configuration
    download_images: bool = True
    save_metadata: bool = True
    log_level: str = "INFO"
    
    # Video file extensions
    supported_extensions: List[str] = field(default_factory=lambda: [
        '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v'
    ])
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.source_directory:
            raise ValueError("source_directory cannot be empty")
        if not self.target_directory:
            raise ValueError("target_directory cannot be empty")
        if self.max_concurrent_files < 1:
            raise ValueError("max_concurrent_files must be at least 1")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts cannot be negative")
        if self.browser_timeout < 1:
            raise ValueError("browser_timeout must be at least 1 second")
        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError("log_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        
        # Normalize extensions to lowercase with dots
        self.supported_extensions = [
            ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
            for ext in self.supported_extensions
        ]
    
    def is_supported_extension(self, extension: str) -> bool:
        """Check if the file extension is supported."""
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = f'.{ext}'
        return ext in self.supported_extensions
    
    def validate_directories(self) -> List[str]:
        """Validate directory paths and return any errors."""
        errors = []
        
        if self.source_directory == self.target_directory:
            errors.append("source_directory and target_directory cannot be the same")
        
        return errors