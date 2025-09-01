"""Statistics command implementation."""

import argparse
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class StatsCommand(BaseCommand):
    """Command to show detailed application statistics."""
    
    @property
    def name(self) -> str:
        return 'stats'
    
    @property
    def description(self) -> str:
        return 'Show detailed application statistics and metrics'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add stats command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper stats                     # Show current session statistics
  av-scraper stats --historical        # Show historical statistics
  av-scraper stats --component scraper # Show scraper-specific stats
  av-scraper stats --export stats.json # Export statistics to file
            """
        )
        
        parser.add_argument(
            '--component',
            choices=['scraper', 'organizer', 'downloader', 'error_handler'],
            help='Show statistics for specific component'
        )
        
        parser.add_argument(
            '--historical',
            action='store_true',
            help='Show historical statistics (if available)'
        )
        
        parser.add_argument(
            '--period',
            choices=['hour', 'day', 'week', 'month'],
            default='day',
            help='Time period for historical stats (default: day)'
        )
        
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format (default: table)'
        )
        
        parser.add_argument(
            '--export',
            type=str,
            help='Export statistics to file'
        )
        
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset current session statistics'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the stats command."""
        app = self._validate_app_required(app)
        
        try:
            # Handle reset request
            if args.reset:
                return await self._reset_statistics(app, args)
            
            # Get current statistics
            current_stats = self._get_current_statistics(app, args)
            
            # Get historical statistics if requested
            historical_stats = None
            if args.historical:
                historical_stats = await self._get_historical_statistics(app, args)
            
            # Prepare complete statistics
            complete_stats = {
                'current': current_stats,
                'timestamp': self._get_timestamp()
            }
            
            if historical_stats:
                complete_stats['historical'] = historical_stats
            
            # Export if requested
            if args.export:
                await self._export_statistics(complete_stats, args.export, args.format)
            
            # Display statistics
            if not args.json:
                self._display_statistics(complete_stats, args)
            
            return self._format_result(
                success=True,
                message="Statistics retrieved successfully",
                statistics=complete_stats
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Failed to get statistics: {e}",
                error=str(e)
            )
    
    def _get_current_statistics(self, app: AVMetadataScraper, args: argparse.Namespace) -> Dict[str, Any]:
        """Get current session statistics."""
        status = app.get_status()
        
        stats = {
            'session': status['processing_stats'],
            'application': {
                'is_running': status['is_running'],
                'active_tasks': status['active_tasks'],
                'queue_size': status['queue_size']
            }
        }
        
        # Add component-specific statistics
        if args.component:
            if args.component in status['component_stats']:
                stats['component'] = {
                    args.component: status['component_stats'][args.component]
                }
        else:
            stats['components'] = status['component_stats']
        
        # Add progress information
        if 'progress' in status and status['progress']:
            stats['progress'] = status['progress']
        
        return stats
    
    async def _get_historical_statistics(self, app: AVMetadataScraper, args: argparse.Namespace) -> Dict[str, Any]:
        """Get historical statistics (placeholder - would need to be implemented)."""
        # This would require implementing statistics persistence
        # For now, return placeholder data
        
        period_hours = {
            'hour': 1,
            'day': 24,
            'week': 168,
            'month': 720
        }
        
        hours = period_hours.get(args.period, 24)
        
        # Placeholder historical data
        return {
            'period': args.period,
            'hours_covered': hours,
            'total_files_processed': 0,
            'average_processing_time': 0.0,
            'success_rate': 0.0,
            'error_count': 0,
            'note': "Historical statistics not yet implemented"
        }
    
    async def _reset_statistics(self, app: AVMetadataScraper, args: argparse.Namespace) -> Dict[str, Any]:
        """Reset current session statistics."""
        # This would need to be implemented in the main application
        # For now, just return a message
        
        return self._format_result(
            success=True,
            message="Statistics reset functionality not yet implemented",
            note="This feature requires implementation in the main application"
        )
    
    def _display_statistics(self, stats: Dict[str, Any], args: argparse.Namespace) -> None:
        """Display statistics in the requested format."""
        if args.format == 'table':
            self._display_table_format(stats, args)
        elif args.format == 'csv':
            self._display_csv_format(stats, args)
        # JSON format is handled by the main CLI
    
    def _display_table_format(self, stats: Dict[str, Any], args: argparse.Namespace) -> None:
        """Display statistics in table format."""
        print("AV Metadata Scraper Statistics")
        print("=" * 50)
        
        # Current session statistics
        if 'current' in stats:
            current = stats['current']
            
            print("\nCurrent Session:")
            print("-" * 20)
            
            if 'session' in current:
                session_stats = current['session']
                print(f"Files Scanned:      {session_stats.get('files_scanned', 0)}")
                print(f"Files Processed:    {session_stats.get('files_processed', 0)}")
                print(f"Files Organized:    {session_stats.get('files_organized', 0)}")
                print(f"Metadata Scraped:   {session_stats.get('metadata_scraped', 0)}")
                print(f"Images Downloaded:  {session_stats.get('images_downloaded', 0)}")
                print(f"Errors Encountered: {session_stats.get('errors_encountered', 0)}")
                print(f"Success Rate:       {session_stats.get('success_rate', 0):.1f}%")
                
                if session_stats.get('duration'):
                    print(f"Duration:           {session_stats['duration']:.1f} seconds")
            
            if 'application' in current:
                app_stats = current['application']
                print(f"\nApplication Status:")
                print(f"Running:            {'Yes' if app_stats.get('is_running') else 'No'}")
                print(f"Active Tasks:       {app_stats.get('active_tasks', 0)}")
                print(f"Queue Size:         {app_stats.get('queue_size', 0)}")
            
            # Component statistics
            if 'components' in current:
                print(f"\nComponent Statistics:")
                print("-" * 20)
                
                for component, component_stats in current['components'].items():
                    print(f"\n{component.title()}:")
                    if isinstance(component_stats, dict):
                        for key, value in component_stats.items():
                            if isinstance(value, (int, float)):
                                if key.endswith('_rate') or key.endswith('_percentage'):
                                    print(f"  {key.replace('_', ' ').title()}: {value:.1f}%")
                                else:
                                    print(f"  {key.replace('_', ' ').title()}: {value}")
            
            elif 'component' in current:
                # Single component statistics
                component_name = list(current['component'].keys())[0]
                component_stats = current['component'][component_name]
                
                print(f"\n{component_name.title()} Statistics:")
                print("-" * 20)
                
                if isinstance(component_stats, dict):
                    for key, value in component_stats.items():
                        if isinstance(value, (int, float)):
                            if key.endswith('_rate') or key.endswith('_percentage'):
                                print(f"{key.replace('_', ' ').title()}: {value:.1f}%")
                            else:
                                print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Historical statistics
        if 'historical' in stats:
            historical = stats['historical']
            print(f"\nHistorical Statistics ({historical.get('period', 'unknown')} period):")
            print("-" * 20)
            
            for key, value in historical.items():
                if key != 'period':
                    if isinstance(value, (int, float)):
                        if key.endswith('_rate') or key.endswith('_percentage'):
                            print(f"{key.replace('_', ' ').title()}: {value:.1f}%")
                        else:
                            print(f"{key.replace('_', ' ').title()}: {value}")
                    else:
                        print(f"{key.replace('_', ' ').title()}: {value}")
        
        print(f"\nGenerated: {stats.get('timestamp', 'Unknown')}")
    
    def _display_csv_format(self, stats: Dict[str, Any], args: argparse.Namespace) -> None:
        """Display statistics in CSV format."""
        import csv
        import sys
        
        writer = csv.writer(sys.stdout)
        
        # Write header
        writer.writerow(['Category', 'Metric', 'Value'])
        
        # Write current session data
        if 'current' in stats and 'session' in stats['current']:
            session_stats = stats['current']['session']
            for key, value in session_stats.items():
                writer.writerow(['Session', key.replace('_', ' ').title(), value])
        
        # Write component data
        if 'current' in stats and 'components' in stats['current']:
            for component, component_stats in stats['current']['components'].items():
                if isinstance(component_stats, dict):
                    for key, value in component_stats.items():
                        writer.writerow([component.title(), key.replace('_', ' ').title(), value])
    
    async def _export_statistics(self, stats: Dict[str, Any], filename: str, format_type: str) -> None:
        """Export statistics to file."""
        from pathlib import Path
        
        output_path = Path(filename)
        
        if format_type == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, default=str)
        
        elif format_type == 'csv':
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Category', 'Metric', 'Value', 'Timestamp'])
                
                timestamp = stats.get('timestamp', '')
                
                # Export current session data
                if 'current' in stats and 'session' in stats['current']:
                    session_stats = stats['current']['session']
                    for key, value in session_stats.items():
                        writer.writerow(['Session', key.replace('_', ' ').title(), value, timestamp])
        
        else:  # table format
            with open(output_path, 'w', encoding='utf-8') as f:
                # Redirect stdout temporarily to capture table output
                import sys
                original_stdout = sys.stdout
                sys.stdout = f
                
                try:
                    self._display_table_format(stats, args)
                finally:
                    sys.stdout = original_stdout
        
        print(f"Statistics exported to: {output_path}")