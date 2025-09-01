"""Base scraper abstract class."""

from abc import ABC, abstractmethod
from typing import Optional
from ..models.movie_metadata import MovieMetadata


class BaseScraper(ABC):
    """Abstract base class for all metadata scrapers."""
    
    def __init__(self, name: str):
        """Initialize the scraper with a name."""
        self.name = name
        self._available = None
    
    @abstractmethod
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """
        Search for movie metadata by code.
        
        Args:
            code: The movie code to search for
            
        Returns:
            MovieMetadata if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the scraper is currently available.
        
        Returns:
            True if the scraper can be used, False otherwise
        """
        pass
    
    async def test_connection(self) -> bool:
        """
        Test the connection to the data source.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return await self.is_available()
        except Exception:
            return False
    
    def __str__(self) -> str:
        """String representation of the scraper."""
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the scraper."""
        return self.__str__()