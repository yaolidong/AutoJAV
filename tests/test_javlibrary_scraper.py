"""Tests for JavLibrary scraper."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import date, datetime
from bs4 import BeautifulSoup

try:
    from aiohttp import ClientResponse
except ImportError:
    # Create a mock ClientResponse for testing if aiohttp is not available
    class ClientResponse:
        def __init__(self):
            self.status = 200
            self.url = ""

from src.scrapers.javlibrary_scraper import JavLibraryScraper
from src.models.movie_metadata import MovieMetadata
from src.utils.http_client import HttpClient


class TestJavLibraryScraper:
    """Test cases for JavLibrary scraper."""
    
    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        client = Mock(spec=HttpClient)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client
    
    @pytest.fixture
    def scraper(self, mock_http_client):
        """Create a JavLibrary scraper instance."""
        return JavLibraryScraper(http_client=mock_http_client)
    
    @pytest.fixture
    def sample_movie_html(self):
        """Sample HTML content for a movie page."""
        return """
        <html>
        <head><title>SSIS-001 Test Movie</title></head>
        <body>
            <div id="video_title">
                <h3><a style="color: blue;">Test Movie Title</a></h3>
            </div>
            <div id="video_info">
                <table>
                    <tr><td>Release Date:</td><td>2021-01-15</td></tr>
                    <tr><td>Runtime:</td><td>120 min</td></tr>
                </table>
            </div>
            <div id="video_cast" class="cast">
                <a href="vl_star.php?s=abc">Test Actress</a>
                <a href="vl_star.php?s=def">Another Actress</a>
            </div>
            <div id="video_maker">
                <a href="vl_maker.php?m=123">Test Studio</a>
            </div>
            <div id="video_series">
                <a href="vl_series.php?s=456">Test Series</a>
            </div>
            <div id="video_genres">
                <a href="vl_genre.php?g=1">Drama</a>
                <a href="vl_genre.php?g=2">Romance</a>
            </div>
            <div id="video_jacket">
                <img id="video_jacket_img" src="/jacket/ssis001.jpg" />
            </div>
            <div id="video_screenshots">
                <img src="/sample/ssis001_1.jpg" />
                <img src="/sample/ssis001_2.jpg" />
            </div>
        </body>
        </html>
        """
    
    @pytest.fixture
    def sample_search_results_html(self):
        """Sample HTML content for search results."""
        return """
        <html>
        <body>
            <div class="videos">
                <div class="video">
                    <a href="vl_movie.php?v=javlissis001">SSIS-001 Test Movie</a>
                </div>
                <div class="video">
                    <a href="vl_movie.php?v=javlissis002">SSIS-002 Another Movie</a>
                </div>
            </div>
        </body>
        </html>
        """
    
    def test_init_default_params(self):
        """Test scraper initialization with default parameters."""
        scraper = JavLibraryScraper()
        
        assert scraper.name == "JavLibrary"
        assert scraper.language == "en"
        assert scraper.BASE_URL == "https://www.javlibrary.com"
        assert isinstance(scraper.http_client, HttpClient)
    
    def test_init_japanese_language(self):
        """Test scraper initialization with Japanese language."""
        scraper = JavLibraryScraper(language="ja")
        
        assert scraper.language == "ja"
        assert scraper.BASE_URL == "https://www.javlibrary.com/ja"
        assert scraper.SEARCH_URL == "https://www.javlibrary.com/ja/vl_searchbyid.php"
    
    @pytest.mark.asyncio
    async def test_is_available_success(self, scraper, mock_http_client):
        """Test availability check when site is accessible."""
        # Mock successful response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await scraper.is_available()
        
        assert result is True
        mock_http_client.get.assert_called_once_with(scraper.BASE_URL)
    
    @pytest.mark.asyncio
    async def test_is_available_failure(self, scraper, mock_http_client):
        """Test availability check when site is not accessible."""
        # Mock failed response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 404
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await scraper.is_available()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_available_exception(self, scraper, mock_http_client):
        """Test availability check when exception occurs."""
        # Mock exception
        mock_http_client.get.side_effect = Exception("Network error")
        
        result = await scraper.is_available()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_available_cached(self, scraper):
        """Test that availability result is cached."""
        # Set up cache
        scraper._availability_cache = True
        scraper._cache_timestamp = datetime.now()
        
        result = await scraper.is_available()
        
        assert result is True
        # Should not make any HTTP requests due to cache
        scraper.http_client.get.assert_not_called()
    
    def test_clean_code_for_search(self, scraper):
        """Test code cleaning for search."""
        test_cases = [
            ("SSIS-001", "SSIS001"),
            ("ssis-001", "SSIS001"),
            ("SSIS_001", "SSIS001"),
            ("SSIS 001", "SSIS001"),
            ("  SSIS-001  ", "SSIS001"),
        ]
        
        for input_code, expected in test_cases:
            result = scraper._clean_code_for_search(input_code)
            assert result == expected
    
    def test_calculate_code_match_score(self, scraper):
        """Test code matching score calculation."""
        # Exact match
        assert scraper._calculate_code_match_score("SSIS001", "SSIS001") == 100
        
        # Partial matches
        assert scraper._calculate_code_match_score("SSIS001", "SSIS") == 90
        assert scraper._calculate_code_match_score("SSIS", "SSIS001") == 90
        
        # Same prefix, different numbers
        assert scraper._calculate_code_match_score("SSIS001", "SSIS002") == 70
        assert scraper._calculate_code_match_score("SSIS001", "SSIS010") == 0  # Too far apart
        
        # Same prefix, same numbers
        assert scraper._calculate_code_match_score("SSIS001", "SSIS001") == 100
        
        # No match
        assert scraper._calculate_code_match_score("ABCD123", "EFGH456") == 0
    
    def test_parse_search_results(self, scraper, sample_search_results_html):
        """Test parsing of search results."""
        soup = BeautifulSoup(sample_search_results_html, 'html.parser')
        
        # Test finding exact match
        result = scraper._parse_search_results(soup, "SSIS-001")
        assert result == "vl_movie.php?v=javlissis001"
        
        # Test finding partial match
        result = scraper._parse_search_results(soup, "SSIS001")
        assert result == "vl_movie.php?v=javlissis001"
    
    def test_parse_search_results_no_match(self, scraper):
        """Test parsing search results with no matches."""
        html = "<html><body><div>No results</div></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper._parse_search_results(soup, "NONEXISTENT")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_by_code_direct_redirect(self, scraper, mock_http_client):
        """Test search when directly redirected to movie page."""
        # Mock response that redirects to movie page
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.url = "https://www.javlibrary.com/en/vl_movie.php?v=javlissis001"
        mock_response.text = AsyncMock(return_value="<html></html>")
        
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await scraper._search_by_code("SSIS-001")
        
        assert result == "https://www.javlibrary.com/en/vl_movie.php?v=javlissis001"
    
    @pytest.mark.asyncio
    async def test_search_by_code_search_results(self, scraper, mock_http_client, sample_search_results_html):
        """Test search when getting search results page."""
        # Mock response with search results
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.url = "https://www.javlibrary.com/en/vl_searchbyid.php"
        mock_response.text = AsyncMock(return_value=sample_search_results_html)
        
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await scraper._search_by_code("SSIS-001")
        
        assert result == "https://www.javlibrary.com/vl_movie.php?v=javlissis001"
    
    @pytest.mark.asyncio
    async def test_search_by_code_failure(self, scraper, mock_http_client):
        """Test search when request fails."""
        # Mock failed response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 404
        
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await scraper._search_by_code("SSIS-001")
        
        assert result is None
    
    def test_extract_title(self, scraper, sample_movie_html):
        """Test title extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_title(soup)
        
        assert result == "Test Movie Title"
    
    def test_extract_actresses(self, scraper, sample_movie_html):
        """Test actress extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_actresses(soup)
        
        assert result == ["Test Actress", "Another Actress"]
    
    def test_extract_release_date(self, scraper, sample_movie_html):
        """Test release date extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_release_date(soup)
        
        assert result == date(2021, 1, 15)
    
    def test_extract_duration(self, scraper, sample_movie_html):
        """Test duration extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_duration(soup)
        
        assert result == 120
    
    def test_extract_studio(self, scraper, sample_movie_html):
        """Test studio extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_studio(soup)
        
        assert result == "Test Studio"
    
    def test_extract_series(self, scraper, sample_movie_html):
        """Test series extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_series(soup)
        
        assert result == "Test Series"
    
    def test_extract_genres(self, scraper, sample_movie_html):
        """Test genre extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_genres(soup)
        
        assert result == ["Drama", "Romance"]
    
    def test_extract_cover_image(self, scraper, sample_movie_html):
        """Test cover image extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_cover_image(soup)
        
        assert result == "https://www.javlibrary.com/jacket/ssis001.jpg"
    
    def test_extract_screenshots(self, scraper, sample_movie_html):
        """Test screenshot extraction from movie page."""
        soup = BeautifulSoup(sample_movie_html, 'html.parser')
        
        result = scraper._extract_screenshots(soup)
        
        expected = [
            "https://www.javlibrary.com/sample/ssis001_1.jpg",
            "https://www.javlibrary.com/sample/ssis001_2.jpg"
        ]
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_extract_movie_metadata_success(self, scraper, mock_http_client, sample_movie_html):
        """Test successful metadata extraction."""
        # Mock successful response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=sample_movie_html)
        
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        movie_url = "https://www.javlibrary.com/en/vl_movie.php?v=javlissis001"
        result = await scraper._extract_movie_metadata(movie_url, "SSIS-001")
        
        assert isinstance(result, MovieMetadata)
        assert result.code == "SSIS-001"
        assert result.title == "Test Movie Title"
        assert result.actresses == ["Test Actress", "Another Actress"]
        assert result.release_date == date(2021, 1, 15)
        assert result.duration == 120
        assert result.studio == "Test Studio"
        assert result.series == "Test Series"
        assert result.genres == ["Drama", "Romance"]
        assert result.source_url == movie_url
    
    @pytest.mark.asyncio
    async def test_extract_movie_metadata_failure(self, scraper, mock_http_client):
        """Test metadata extraction when request fails."""
        # Mock failed response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 404
        
        mock_http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        movie_url = "https://www.javlibrary.com/en/vl_movie.php?v=nonexistent"
        result = await scraper._extract_movie_metadata(movie_url, "NONEXISTENT")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_movie_success(self, scraper, mock_http_client, sample_movie_html):
        """Test successful movie search."""
        # Mock availability check
        scraper.is_available = AsyncMock(return_value=True)
        
        # Mock search response (direct redirect)
        search_response = Mock(spec=ClientResponse)
        search_response.status = 200
        search_response.url = "https://www.javlibrary.com/en/vl_movie.php?v=javlissis001"
        search_response.text = AsyncMock(return_value="<html></html>")
        
        # Mock movie page response
        movie_response = Mock(spec=ClientResponse)
        movie_response.status = 200
        movie_response.text = AsyncMock(return_value=sample_movie_html)
        
        # Set up mock to return different responses for different calls
        mock_http_client.get.return_value.__aenter__.side_effect = [
            AsyncMock(return_value=search_response)(),
            AsyncMock(return_value=movie_response)()
        ]
        
        result = await scraper.search_movie("SSIS-001")
        
        assert isinstance(result, MovieMetadata)
        assert result.code == "SSIS-001"
        assert result.title == "Test Movie Title"
    
    @pytest.mark.asyncio
    async def test_search_movie_not_available(self, scraper):
        """Test movie search when site is not available."""
        # Mock availability check to return False
        scraper.is_available = AsyncMock(return_value=False)
        
        result = await scraper.search_movie("SSIS-001")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_movie_not_found(self, scraper, mock_http_client):
        """Test movie search when movie is not found."""
        # Mock availability check
        scraper.is_available = AsyncMock(return_value=True)
        
        # Mock search that returns no results
        scraper._search_by_code = AsyncMock(return_value=None)
        
        result = await scraper.search_movie("NONEXISTENT")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_movie_extraction_failure(self, scraper, mock_http_client):
        """Test movie search when metadata extraction fails."""
        # Mock availability check
        scraper.is_available = AsyncMock(return_value=True)
        
        # Mock successful search but failed extraction
        scraper._search_by_code = AsyncMock(return_value="https://example.com/movie")
        scraper._extract_movie_metadata = AsyncMock(return_value=None)
        
        result = await scraper.search_movie("SSIS-001")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_movie_exception(self, scraper):
        """Test movie search when exception occurs."""
        # Mock availability check to raise exception
        scraper.is_available = AsyncMock(side_effect=Exception("Network error"))
        
        result = await scraper.search_movie("SSIS-001")
        
        assert result is None
    
    def test_extract_methods_with_empty_html(self, scraper):
        """Test extraction methods with empty/minimal HTML."""
        empty_soup = BeautifulSoup("<html><body></body></html>", 'html.parser')
        
        # All extraction methods should handle empty HTML gracefully
        assert scraper._extract_title(empty_soup) is None
        assert scraper._extract_actresses(empty_soup) == []
        assert scraper._extract_release_date(empty_soup) is None
        assert scraper._extract_duration(empty_soup) is None
        assert scraper._extract_studio(empty_soup) is None
        assert scraper._extract_series(empty_soup) is None
        assert scraper._extract_genres(empty_soup) == []
        assert scraper._extract_description(empty_soup) is None
        assert scraper._extract_rating(empty_soup) is None
        assert scraper._extract_cover_image(empty_soup) is None
        assert scraper._extract_screenshots(empty_soup) == []
    
    def test_extract_rating_various_formats(self, scraper):
        """Test rating extraction with various formats."""
        test_cases = [
            ('<div class="rating">8.5/10</div>', 8.5),
            ('<div class="score">4.2/5</div>', 8.4),  # Normalized to 10-point scale
            ('<div class="rating">Rating: 7.8</div>', 7.8),
            ('<div class="rating">No rating</div>', None),
        ]
        
        for html, expected in test_cases:
            soup = BeautifulSoup(f"<html><body>{html}</body></html>", 'html.parser')
            result = scraper._extract_rating(soup)
            if expected is None:
                assert result is None
            else:
                assert abs(result - expected) < 0.1
    
    def test_extract_duration_various_formats(self, scraper):
        """Test duration extraction with various formats."""
        test_cases = [
            ('<div id="video_info">Runtime: 120 min</div>', 120),
            ('<div id="video_info">時間: 90分</div>', 90),
            ('<div id="video_info">No duration info</div>', None),
        ]
        
        for html, expected in test_cases:
            soup = BeautifulSoup(f"<html><body>{html}</body></html>", 'html.parser')
            result = scraper._extract_duration(soup)
            assert result == expected
    
    def test_extract_release_date_various_formats(self, scraper):
        """Test release date extraction with various formats."""
        test_cases = [
            ('<div id="video_info">Release: 2021-01-15</div>', date(2021, 1, 15)),
            ('<div id="video_info">Date: 2021/01/15</div>', date(2021, 1, 15)),
            ('<div id="video_info">Invalid date</div>', None),
            ('<div id="video_info">2050-01-01</div>', None),  # Future date should be rejected
        ]
        
        for html, expected in test_cases:
            soup = BeautifulSoup(f"<html><body>{html}</body></html>", 'html.parser')
            result = scraper._extract_release_date(soup)
            assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])