#!/usr/bin/env python3
"""
AV Metadata Scraper CLI Entry Point

This script provides the command-line interface for the AV Metadata Scraper.
It can be used directly or installed as a console script.
"""

import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli import main


if __name__ == "__main__":
    sys.exit(main())