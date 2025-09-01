#!/usr/bin/env python3
"""
Simple test to check basic module structure without external dependencies.
"""

import sys
from pathlib import Path

def test_basic_imports():
    """Test basic module imports without external dependencies."""
    print("🔍 Testing basic module structure...\n")
    
    success_count = 0
    total_count = 0
    
    # Test basic module structure
    basic_tests = [
        # Test if modules can be found (not imported due to dependencies)
        ("src", "Main package exists"),
        ("src.models", "Models package exists"),
        ("src.utils", "Utils package exists"),
        ("src.cli", "CLI package exists"),
    ]
    
    for module_name, description in basic_tests:
        total_count += 1
        try:
            # Just check if the module path exists
            module_path = Path(module_name.replace('.', '/'))
            init_file = module_path / '__init__.py'
            
            if init_file.exists():
                print(f"✅ {module_name} - {description}")
                success_count += 1
            else:
                print(f"❌ {module_name} - {description}: __init__.py not found")
        except Exception as e:
            print(f"❌ {module_name} - {description}: {e}")
    
    # Test individual files exist
    file_tests = [
        ("src/main_application.py", "Main application file"),
        ("src/models/config.py", "Config model"),
        ("src/models/video_file.py", "Video file model"),
        ("src/models/movie_metadata.py", "Movie metadata model"),
        ("src/utils/logging_config.py", "Logging config"),
        ("src/utils/error_handler.py", "Error handler"),
        ("src/scanner/file_scanner.py", "File scanner"),
        ("src/scrapers/base_scraper.py", "Base scraper"),
        ("src/organizers/file_organizer.py", "File organizer"),
        ("src/config/config_manager.py", "Config manager"),
    ]
    
    for file_path, description in file_tests:
        total_count += 1
        if Path(file_path).exists():
            print(f"✅ {file_path} - {description}")
            success_count += 1
        else:
            print(f"❌ {file_path} - {description}: File not found")
    
    print(f"\n📊 Results: {success_count}/{total_count} checks passed")
    
    if success_count == total_count:
        print("🎉 All basic structure checks passed!")
        return 0
    else:
        print("⚠️  Some structure checks failed.")
        return 1

if __name__ == "__main__":
    sys.exit(test_basic_imports())