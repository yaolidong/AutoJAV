"""Main CLI application class and entry point."""

import argparse
import asyncio
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..utils.logging_config import LogLevel, get_logger
from ..main_application import AVMetadataScraper
from .config_wizard import ConfigWizard
from .commands import (
    ScanCommand, ProcessCommand, StatusCommand, StopCommand,
    ConfigCommand, HealthCommand, StatsCommand
)
from .commands.advanced_command import AdvancedCommand


class AVScraperCLI:
    """
    Command Line Interface for AV Metadata Scraper.
    
    Provides a comprehensive CLI with commands for configuration, processing,
    monitoring, and debugging the AV metadata scraping application.
    """
    
    def __init__(self):
        """Initialize the CLI application."""
        self.app: Optional[AVMetadataScraper] = None
        self.logger = get_logger(__name__)
        self.commands = self._register_commands()
    
    def _register_commands(self) -> Dict[str, Any]:
        """Register all available CLI commands."""
        return {
            'scan': ScanCommand(),
            'process': ProcessCommand(),
            'status': StatusCommand(),
            'stop': StopCommand(),
            'config': ConfigCommand(),
            'health': HealthCommand(),
            'stats': StatsCommand(),
            'advanced': AdvancedCommand(),
        }
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser with all commands and options."""
        parser = argparse.ArgumentParser(
            prog='av-scraper',
            description='AV Metadata Scraper - Automated video file organization and metadata scraping',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  av-scraper process                    # Process all files with default config
  av-scraper process --config custom.yaml --dry-run
  av-scraper scan --source /videos     # Scan specific directory
  av-scraper config wizard             # Interactive configuration setup
  av-scraper status --json             # Get status in JSON format
  av-scraper test scrapers             # Test scraper connectivity
  av-scraper health --verbose          # Detailed health check
            """
        )
        
        # Global options
        parser.add_argument(
            '--config', '-c',
            type=Path,
            help='Path to configuration file (default: config/config.yaml)'
        )
        
        parser.add_argument(
            '--log-level', '-l',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            help='Set logging level (default: INFO)'
        )
        
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress console output (only log to file)'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format'
        )
        
        parser.add_argument(
            '--version',
            action='version',
            version='AV Metadata Scraper 1.0.0'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands',
            metavar='COMMAND'
        )
        
        # Register command parsers
        for command_name, command_obj in self.commands.items():
            command_obj.add_parser(subparsers)
        
        return parser
    
    async def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI application.
        
        Args:
            args: Command line arguments (defaults to sys.argv)
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Configure logging based on arguments
        self._configure_logging(parsed_args)
        
        try:
            # Handle no command specified
            if not parsed_args.command:
                parser.print_help()
                return 0
            
            # Initialize application if needed
            if parsed_args.command in ['process', 'scan', 'status', 'stop', 'health']:
                self.app = AVMetadataScraper(parsed_args.config)
            
            # Execute the command
            command = self.commands[parsed_args.command]
            result = await command.execute(parsed_args, self.app)
            
            # Handle output formatting
            if parsed_args.json and isinstance(result, dict):
                print(json.dumps(result, indent=2, default=str))
            elif result is not None:
                if isinstance(result, dict):
                    self._print_formatted_result(result, parsed_args.verbose)
                else:
                    print(result)
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("Operation cancelled by user")
            if self.app and self.app.is_running:
                await self.app.stop()
            return 130  # Standard exit code for SIGINT
            
        except Exception as e:
            self.logger.error(f"CLI error: {e}")
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def _configure_logging(self, args: argparse.Namespace) -> None:
        """Configure logging based on CLI arguments."""
        # Set log level
        if hasattr(args, 'log_level') and args.log_level:
            import logging
            logging.getLogger().setLevel(getattr(logging, args.log_level))
        
        # Handle quiet mode
        if hasattr(args, 'quiet') and args.quiet:
            import logging
            # Disable console logging
            console_handlers = [
                h for h in logging.getLogger().handlers 
                if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
            ]
            for handler in console_handlers:
                logging.getLogger().removeHandler(handler)
    
    def _print_formatted_result(self, result: Dict[str, Any], verbose: bool = False) -> None:
        """Print formatted result to console."""
        if 'status' in result:
            print(f"Status: {result['status']}")
        
        if 'message' in result:
            print(f"Message: {result['message']}")
        
        if verbose and 'details' in result:
            print("\nDetails:")
            self._print_dict_recursive(result['details'], indent=2)
        
        if 'statistics' in result:
            print("\nStatistics:")
            self._print_dict_recursive(result['statistics'], indent=2)
    
    def _print_dict_recursive(self, data: Dict[str, Any], indent: int = 0) -> None:
        """Recursively print dictionary with proper indentation."""
        for key, value in data.items():
            prefix = " " * indent
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._print_dict_recursive(value, indent + 2)
            elif isinstance(value, list):
                print(f"{prefix}{key}: [{len(value)} items]")
                if len(value) <= 5:  # Show first few items
                    for item in value:
                        print(f"{prefix}  - {item}")
            else:
                print(f"{prefix}{key}: {value}")


def main() -> int:
    """Main entry point for the CLI application."""
    cli = AVScraperCLI()
    
    try:
        # Run the CLI application
        return asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())