#!/usr/bin/env python3
"""
AV Metadata Scraper - Main Entry Point

A Docker-based automated video metadata scraping and organizing system.
This script can run in CLI mode or direct execution mode.
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def parse_arguments():
    """Parse command line arguments to determine execution mode."""
    parser = argparse.ArgumentParser(
        description='AV Metadata Scraper',
        add_help=False  # We'll handle help in CLI mode
    )
    
    parser.add_argument(
        '--cli',
        action='store_true',
        help='Run in CLI mode with full command interface'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='Run in watch mode for continuous monitoring'
    )
    
    # Parse known args to avoid conflicts with CLI subcommands
    args, remaining = parser.parse_known_args()
    
    return args, remaining


async def run_direct_mode(config_path=None, watch_mode=False):
    """Run in direct mode - start processing immediately.
    
    Args:
        config_path: Path to configuration file
        watch_mode: Whether to run in continuous watch mode
    """
    from src.main_application import AVMetadataScraper
    from src.utils.logging_config import LoggingConfig, LogLevel
    
    # Setup basic logging
    logging_config = LoggingConfig(
        log_level=LogLevel.INFO,
        log_dir=Path("logs"),
        console_logging=True,
        file_logging=True
    )
    logging_config.setup_logging()
    
    try:
        # Create and start the application
        app = AVMetadataScraper(config_path)
        
        if watch_mode:
            # Run in continuous watch mode
            print("Starting in WATCH MODE - monitoring for new files...")
            await app.start_watch_mode()
        else:
            # Run once and exit
            await app.start()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


async def run_cli_mode(remaining_args):
    """Run in CLI mode with full command interface."""
    from src.cli import AVScraperCLI
    
    cli = AVScraperCLI()
    return await cli.run(remaining_args)


async def main():
    """Main entry point that determines execution mode."""
    args, remaining = parse_arguments()
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    if args.cli or remaining:
        # CLI mode - either explicitly requested or has subcommands
        exit_code = await run_cli_mode(remaining)
        sys.exit(exit_code)
    else:
        # Direct mode - start processing immediately
        await run_direct_mode(args.config, args.watch)


if __name__ == "__main__":
    asyncio.run(main())