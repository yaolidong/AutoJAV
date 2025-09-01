"""Tests for scrapers."""
import pytest

from src.scrapers import BaseScraper, JavDBScraper, JavLibraryScraper


class TestBaseScraper:
    """Test BaseScraper abstract class."""
    
    def test_cannot_instantiate_base_scraper(self):
        """Test that BaseScraper cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseScraper("test")


class TestJavDBScraper:
    """Test JavDBScraper."""
    
    def test_javdb_scraper_creation(self):
        """Test JavDBScraper creation."""
        scraper = JavDBScraper()
        assert scraper.name == "JavDB"
        assert str(scraper) == "JavDBScraper(JavDB)"
    
    def test_is_available(self):
        """Test is_available method."""
        scraper = JavDBScraper()
        assert scraper.is_available() is True
    
    def test_search_movie_not_implemented(self):
        """Test that search_movie raises NotImplementedError."""
        scraper = JavDBScraper()
        with pytest.raises(NotImplementedError):
            scraper.search_movie("ABC-123")
    
    def test_login_if_needed_not_implemented(self):
        """Test that login_if_needed raises NotImplementedError."""
        scraper = JavDBScraper()
        with pytest.raises(NotImplementedError):
            scraper.login_if_needed()


class TestJavLibraryScraper:
    """Test JavLibraryScraper."""
    
    def test_javlibrary_scraper_creation(self):
        """Test JavLibraryScraper creation."""
        scraper = JavLibraryScraper()
        assert scraper.name == "JavLibrary"
        assert str(scraper) == "JavLibraryScraper(JavLibrary)"
    
    def test_is_available(self):
        """Test is_available method."""
        scraper = JavLibraryScraper()
        assert scraper.is_available() is True
    
    def test_search_movie_not_implemented(self):
        """Test that search_movie raises NotImplementedError."""
        scraper = JavLibraryScraper()
        with pytest.raises(NotImplementedError):
            scraper.search_movie("ABC-123")