"""Base command class for CLI commands."""

import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ...main_application import AVMetadataScraper


class BaseCommand(ABC):
    """
    Base class for all CLI commands.
    
    Provides common functionality and interface for command implementations.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description."""
        pass
    
    @abstractmethod
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """
        Add command parser to subparsers.
        
        Args:
            subparsers: Subparsers action from main parser
            
        Returns:
            Command-specific argument parser
        """
        pass
    
    @abstractmethod
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Any:
        """
        Execute the command.
        
        Args:
            args: Parsed command line arguments
            app: Application instance (if needed)
            
        Returns:
            Command result (can be None, dict, string, etc.)
        """
        pass
    
    def _create_parser(self, subparsers: argparse._SubParsersAction, **kwargs) -> argparse.ArgumentParser:
        """
        Create a parser for this command with common options.
        
        Args:
            subparsers: Subparsers action from main parser
            **kwargs: Additional arguments for add_parser
            
        Returns:
            Command parser
        """
        parser = subparsers.add_parser(
            self.name,
            description=self.description,
            help=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            **kwargs
        )
        
        return parser
    
    def _format_result(self, success: bool, message: str, **kwargs) -> Dict[str, Any]:
        """
        Format command result in standard format.
        
        Args:
            success: Whether the command succeeded
            message: Result message
            **kwargs: Additional result data
            
        Returns:
            Formatted result dictionary
        """
        result = {
            'success': success,
            'message': message,
            'timestamp': self._get_timestamp()
        }
        
        result.update(kwargs)
        return result
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _validate_app_required(self, app: Optional[AVMetadataScraper]) -> AVMetadataScraper:
        """
        Validate that app instance is provided when required.
        
        Args:
            app: Application instance
            
        Returns:
            Validated app instance
            
        Raises:
            ValueError: If app is None
        """
        if app is None:
            raise ValueError("Application instance is required for this command")
        return app