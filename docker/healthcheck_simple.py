#!/usr/bin/env python3
"""
Simple Docker Health Check for NAS compatibility
Minimal checks to avoid resource exhaustion
"""

import sys
import os
from pathlib import Path

def main():
    """Simple health check that just verifies basic functionality."""
    try:
        # Check if critical directories exist
        critical_dirs = ['/app/source', '/app/target', '/app/config']
        for dir_path in critical_dirs:
            if not Path(dir_path).exists():
                print(f"Directory {dir_path} not found")
                sys.exit(1)
        
        # Check if config file exists
        if not Path('/app/config/config.yaml').exists():
            print("Config file not found")
            sys.exit(1)
        
        # Try to import critical modules (minimal check)
        try:
            import yaml
            import requests
            print("Health check passed")
            sys.exit(0)
        except ImportError as e:
            print(f"Import error: {e}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Health check error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()