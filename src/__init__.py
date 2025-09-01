"""
AV Metadata Scraper

A Docker-based automated video metadata scraping and organizing system
for Japanese AV content.
"""

__version__ = "1.0.0"
__author__ = "AV Metadata Scraper Team"
__description__ = "Automated video metadata scraping and organizing system"

# Main application
from .main_application import AVMetadataScraper

# Core models
from .models import VideoFile, MovieMetadata, Config

# Main components
from .scanner import FileScanner
from .organizers import FileOrganizer
from .downloaders import ImageDownloader
from .scrapers import MetadataScraper, ScraperFactory

# Configuration
from .config import ConfigManager

# CLI
from .cli import main as cli_main, AVScraperCLI

__all__ = [
    # Version info
    '__version__',
    '__author__', 
    '__description__',
    
    # Main application
    'AVMetadataScraper',
    
    # Core models
    'VideoFile',
    'MovieMetadata', 
    'Config',
    
    # Main components
    'FileScanner',
    'FileOrganizer',
    'ImageDownloader',
    'MetadataScraper',
    'ScraperFactory',
    
    # Configuration
    'ConfigManager',
    
    # CLI
    'cli_main',
    'AVScraperCLI'
]