"""Status command implementation."""

import argparse
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class StatusCommand(BaseCommand):
    """Command to show application status and statistics."""
    
    @property
    def name(self) -> str:
        return 'status'
    
    @property
    def description(self) -> str:
        return 'Show current application status and processing statistics'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add status command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper status                    # Show basic status
  av-scraper status --detailed         # Show detailed statistics
  av-scraper status --watch            # Continuously monitor status
  av-scraper status --json             # Output in JSON format
            """
        )
        
        parser.add_argument(
            '--detailed', '-d',
            action='store_true',
            help='Show detailed component statistics'
        )
        
        parser.add_argument(
            '--watch', '-w',
            action='store_true',
            help='Continuously monitor status (update every 2 seconds)'
        )
        
        parser.add_argument(
            '--interval',
            type=int,
            default=2,
            help='Update interval for watch mode (seconds, default: 2)'
        )
        
        parser.add_argument(
            '--components',
            nargs='+',
            choices=['scraper', 'organizer', 'downloader', 'error_handler'],
            help='Show status for specific components only'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the status command."""
        app = self._validate_app_required(app)
        
        try:
            if args.watch:
                await self._watch_status(app, args)
                return self._format_result(
                    success=True,
                    message="Status monitoring stopped"
                )
            else:
                status = app.get_status()
                
                if not args.json:
                    self._print_status(status, args)
                
                return self._format_result(
                    success=True,
                    message="Status retrieved successfully",
                    status=status
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Failed to get status: {e}",
                error=str(e)
            )
    
    async def _watch_status(self, app: AVMetadataScraper, args: argparse.Namespace) -> None:
        """Continuously monitor and display status."""
        import asyncio
        import os
        
        try:
            while True:
                # Clear screen (works on most terminals)
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Get and display current status
                status = app.get_status()
                print(f"AV Metadata Scraper Status (updating every {args.interval}s)")
                print("=" * 60)
                self._print_status(status, args)
                print("\nPress Ctrl+C to stop monitoring...")
                
                # Wait for next update
                await asyncio.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\nStatus monitoring stopped.")
    
    def _print_status(self, status: Dict[str, Any], args: argparse.Namespace) -> None:
        """Print formatted status information."""
        # Application status
        print(f"Application Status: {'Running' if status['is_running'] else 'Stopped'}")
        
        if status['should_stop']:
            print("Status: Shutting down...")
        
        print(f"Active Tasks: {status['active_tasks']}")
        print(f"Queue Size: {status['queue_size']}")
        
        # Processing statistics
        stats = status['processing_stats']
        print(f"\nProcessing Statistics:")
        print(f"  Files Scanned: {stats['files_scanned']}")
        print(f"  Files Processed: {stats['files_processed']}")
        print(f"  Files Organized: {stats['files_organized']}")
        print(f"  Metadata Scraped: {stats['metadata_scraped']}")
        print(f"  Images Downloaded: {stats['images_downloaded']}")
        print(f"  Errors Encountered: {stats['errors_encountered']}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        
        if stats['duration']:
            print(f"  Duration: {stats['duration']:.1f} seconds")
        
        # Progress information
        if 'progress' in status and status['progress']:
            print(f"\nProgress Information:")
            progress = status['progress']
            for task_id, task_progress in progress.items():
                if task_progress.get('active', False):
                    current = task_progress.get('current', 0)
                    total = task_progress.get('total', 0)
                    percentage = (current / total * 100) if total > 0 else 0
                    print(f"  {task_id}: {current}/{total} ({percentage:.1f}%)")
        
        # Component statistics (if detailed or specific components requested)
        if args.detailed or args.components:
            self._print_component_stats(status['component_stats'], args)
    
    def _print_component_stats(self, component_stats: Dict[str, Any], args: argparse.Namespace) -> None:
        """Print detailed component statistics."""
        print(f"\nComponent Statistics:")
        
        components_to_show = args.components if args.components else component_stats.keys()
        
        for component in components_to_show:
            if component in component_stats:
                stats = component_stats[component]
                print(f"\n  {component.title()}:")
                
                if isinstance(stats, dict):
                    for key, value in stats.items():
                        if isinstance(value, (int, float)):
                            if key.endswith('_rate') or key.endswith('_percentage'):
                                print(f"    {key.replace('_', ' ').title()}: {value:.1f}%")
                            else:
                                print(f"    {key.replace('_', ' ').title()}: {value}")
                        else:
                            print(f"    {key.replace('_', ' ').title()}: {value}")
                else:
                    print(f"    Status: {stats}")