#!/usr/bin/env python3
"""
Validation script to check all module imports are working correctly.
"""

import sys
import traceback
from pathlib import Path

def test_import(module_name, description="", optional=False):
    """Test importing a module and report results."""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - {description}")
        return True
    except ImportError as e:
        if optional:
            print(f"⚠️  {module_name} - {description}: {e} (optional)")
            return True  # Don't count optional imports as failures
        else:
            print(f"❌ {module_name} - {description}: {e}")
            return False
    except Exception as e:
        print(f"⚠️  {module_name} - {description}: {e}")
        return False

def main():
    """Run all import tests."""
    print("🔍 Validating module imports...\n")
    
    success_count = 0
    total_count = 0
    
    # Test core modules
    tests = [
        # Core package
        ("src", "Main package"),
        
        # Models
        ("src.models", "Models package"),
        ("src.models.config", "Configuration model"),
        ("src.models.video_file", "Video file model"),
        ("src.models.movie_metadata", "Movie metadata model"),
        
        # Scanner
        ("src.scanner", "Scanner package"),
        ("src.scanner.file_scanner", "File scanner"),
        
        # Scrapers
        ("src.scrapers", "Scrapers package"),
        ("src.scrapers.base_scraper", "Base scraper"),
        ("src.scrapers.javdb_scraper", "JavDB scraper"),
        ("src.scrapers.javlibrary_scraper", "JavLibrary scraper"),
        ("src.scrapers.metadata_scraper", "Metadata scraper"),
        ("src.scrapers.scraper_factory", "Scraper factory"),
        
        # Organizers
        ("src.organizers", "Organizers package"),
        ("src.organizers.file_organizer", "File organizer"),
        
        # Downloaders
        ("src.downloaders", "Downloaders package"),
        ("src.downloaders.image_downloader", "Image downloader"),
        
        # Utils
        ("src.utils", "Utils package"),
        ("src.utils.logging_config", "Logging configuration"),
        ("src.utils.error_handler", "Error handler"),
        ("src.utils.progress_tracker", "Progress tracker"),
        ("src.utils.batch_processor", "Batch processor"),
        ("src.utils.duplicate_detector", "Duplicate detector"),
        ("src.utils.performance_monitor", "Performance monitor"),
        ("src.utils.progress_persistence", "Progress persistence"),
        
        # Config
        ("src.config", "Config package"),
        ("src.config.config_manager", "Config manager"),
        
        # CLI
        ("src.cli", "CLI package"),
        ("src.cli.cli_main", "CLI main"),
        ("src.cli.config_wizard", "Config wizard"),
        ("src.cli.commands", "CLI commands package"),
        
        # Main application
        ("src.main_application", "Main application"),
    ]
    
    for module_name, description in tests:
        total_count += 1
        if test_import(module_name, description):
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{total_count} imports successful")
    
    if success_count == total_count:
        print("🎉 All imports are working correctly!")
        return 0
    else:
        print("⚠️  Some imports failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())