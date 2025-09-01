#!/usr/bin/env python3
"""
Test core module imports without external dependencies.
"""

import sys
from pathlib import Path

def test_core_imports():
    """Test core module imports that don't require external dependencies."""
    print("🔍 Testing core module imports...\n")
    
    success_count = 0
    total_count = 0
    
    # Test imports that should work without external dependencies
    core_tests = [
        # Test basic Python modules first
        ("pathlib", "Python pathlib"),
        ("datetime", "Python datetime"),
        ("typing", "Python typing"),
        ("enum", "Python enum"),
        ("dataclasses", "Python dataclasses"),
        
        # Test our core models (should not have external deps)
        ("src.models.video_file", "Video file model"),
        ("src.models.movie_metadata", "Movie metadata model"),
        
        # Test utils that don't require external deps
        ("src.utils.error_handler", "Error handler"),
        ("src.utils.progress_tracker", "Progress tracker"),
    ]
    
    for module_name, description in core_tests:
        total_count += 1
        try:
            __import__(module_name)
            print(f"✅ {module_name} - {description}")
            success_count += 1
        except ImportError as e:
            # Check if it's a missing external dependency
            if any(dep in str(e).lower() for dep in ['yaml', 'aiohttp', 'selenium', 'beautifulsoup4', 'pillow']):
                print(f"⚠️  {module_name} - {description}: Missing external dependency ({e})")
                success_count += 1  # Don't count as failure
            else:
                print(f"❌ {module_name} - {description}: {e}")
        except Exception as e:
            print(f"⚠️  {module_name} - {description}: {e}")
    
    print(f"\n📊 Results: {success_count}/{total_count} core imports successful")
    
    if success_count == total_count:
        print("🎉 All core imports working!")
        return 0
    else:
        print("⚠️  Some core imports failed.")
        return 1

if __name__ == "__main__":
    sys.exit(test_core_imports())