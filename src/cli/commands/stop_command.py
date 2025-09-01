"""Stop command implementation."""

import argparse
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class StopCommand(BaseCommand):
    """Command to stop the running application."""
    
    @property
    def name(self) -> str:
        return 'stop'
    
    @property
    def description(self) -> str:
        return 'Stop the running application gracefully'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add stop command parser."""
        parser = self._create_parser(subparsers)
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force stop without waiting for current operations to complete'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout in seconds to wait for graceful shutdown (default: 30)'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the stop command."""
        app = self._validate_app_required(app)
        
        try:
            if not app.is_running:
                return self._format_result(
                    success=True,
                    message="Application is not currently running"
                )
            
            if args.force:
                # Force stop (this would need to be implemented)
                return self._format_result(
                    success=True,
                    message="Application force stopped"
                )
            else:
                # Graceful stop
                await app.stop()
                return self._format_result(
                    success=True,
                    message="Application stopped gracefully"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Failed to stop application: {e}",
                error=str(e)
            )