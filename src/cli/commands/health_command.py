"""Health command implementation."""

import argparse
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class HealthCommand(BaseCommand):
    """Command to perform application health checks."""
    
    @property
    def name(self) -> str:
        return 'health'
    
    @property
    def description(self) -> str:
        return 'Perform application health check'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add health command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper health                    # Basic health check
  av-scraper health --detailed         # Detailed health information
  av-scraper health --components scrapers,config  # Check specific components
            """
        )
        
        parser.add_argument(
            '--detailed', '-d',
            action='store_true',
            help='Show detailed health information'
        )
        
        parser.add_argument(
            '--components',
            nargs='+',
            choices=['scrapers', 'organizer', 'configuration', 'network'],
            help='Check specific components only'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout for health checks in seconds (default: 30)'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the health command."""
        app = self._validate_app_required(app)
        
        try:
            # Perform health check
            health_status = await app.health_check()
            
            # Print health status
            if not args.json:
                self._print_health_status(health_status, args)
            
            return self._format_result(
                success=health_status['status'] == 'healthy',
                message=f"Health check completed - Status: {health_status['status']}",
                health_status=health_status
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Health check failed: {e}",
                error=str(e)
            )
    
    def _print_health_status(self, health_status: Dict[str, Any], args: argparse.Namespace) -> None:
        """Print formatted health status."""
        status = health_status['status']
        
        # Overall status
        if status == 'healthy':
            print("🟢 Application Status: HEALTHY")
        elif status == 'degraded':
            print("🟡 Application Status: DEGRADED")
        else:
            print("🔴 Application Status: UNHEALTHY")
        
        print(f"Timestamp: {health_status['timestamp']}")
        
        # Component status
        if 'components' in health_status:
            print("\nComponent Health:")
            
            components_to_show = args.components if args.components else health_status['components'].keys()
            
            for component in components_to_show:
                if component in health_status['components']:
                    component_status = health_status['components'][component]
                    self._print_component_health(component, component_status, args.detailed)
        
        # Issues summary
        if 'issues' in health_status and health_status['issues']:
            print(f"\nIssues Found:")
            for issue in health_status['issues']:
                print(f"  ⚠️  {issue}")
        
        # Error details
        if 'error' in health_status:
            print(f"\nError: {health_status['error']}")
    
    def _print_component_health(self, component: str, status: Dict[str, Any], detailed: bool) -> None:
        """Print health status for a specific component."""
        # Determine status icon
        if isinstance(status, dict):
            if 'errors' in status and status['errors']:
                icon = "🔴"
                status_text = "UNHEALTHY"
            elif 'valid' in status and not status['valid']:
                icon = "🔴"
                status_text = "INVALID"
            elif 'warnings' in status and status['warnings']:
                icon = "🟡"
                status_text = "WARNING"
            else:
                icon = "🟢"
                status_text = "HEALTHY"
        else:
            icon = "🟢"
            status_text = "HEALTHY"
        
        print(f"  {icon} {component.title()}: {status_text}")
        
        # Show details if requested
        if detailed and isinstance(status, dict):
            if 'errors' in status and status['errors']:
                for error in status['errors']:
                    print(f"    ❌ {error}")
            
            if 'warnings' in status and status['warnings']:
                for warning in status['warnings']:
                    print(f"    ⚠️  {warning}")
            
            # Show other status information
            for key, value in status.items():
                if key not in ['errors', 'warnings', 'valid']:
                    if isinstance(value, bool):
                        print(f"    {key}: {'✅' if value else '❌'}")
                    else:
                        print(f"    {key}: {value}")