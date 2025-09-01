"""Tests for JavDBScraper."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date
from bs4 import BeautifulSoup

from src.scrapers.javdb_scraper import JavDBScraper
from src.utils.webdriver_manager import WebDriverManager
from src.utils.login_manager import LoginManager
from src.models.movie_metadata import MovieMetadata


class TestJavDBScraper:
    """Test cases for JavDBScraper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_driver_manager = MagicMock(spec=WebDriverManager)
        self.mock_login_manager = AsyncMock(spec=LoginManager)
        
        # Mock driver manager methods
        self.mock_driver_manager.get_page.return_value = True
        self.mock_driver_manager.get_page_source.return_value = "<html><body>Test</body></html>"
        self.mock_driver_manager.get_current_url.return_value = "https://javdb.com"
        
        # Mock login manager methods
        self.mock_login_manager.is_logged_in.return_value = True
        self.mock_login_manager.login.return_value = True
        
        self.scraper = JavDBScraper(
            driver_manager=self.mock_driver_manager,
            login_manager=self.mock_login_manager
        )
    
    def test_init(self):
        """Test JavDBScraper initialization."""
        assert self.scraper.name == "JavDB"
        assert self.scraper.driver_manager == self.mock_driver_manager
        assert self.scraper.login_manager == self.mock_login_manager
        assert self.scraper.use_login is True
        assert self.scraper.BASE_URL == "https://javdb.com"
    
    def test_init_without_login(self):
        """Test JavDBScraper initialization without login."""
        scraper = JavDBScraper(
            driver_manager=self.mock_driver_manager,
            use_login=False
        )
        
        assert scraper.use_login is False
        assert scraper.login_manager is None
    
    @pytest.mark.asyncio
    async def test_is_available_success(self):
        """Test availability check when JavDB is available."""
        self.mock_driver_manager.get_page.return_value = True
        
        result = await self.scraper.is_available()
        
        assert result is True
        assert self.scraper._availability_cache is True
    
    @pytest.mark.asyncio
    async def test_is_available_failure(self):
        """Test availability check when JavDB is not available."""
        self.mock_driver_manager.get_page.return_value = False
        
        result = await self.scraper.is_available()
        
        assert result is False
        assert self.scraper._availability_cache is False
    
    @pytest.mark.asyncio
    async def test_is_available_cached(self):
        """Test availability check uses cache."""
        # Set cache
        self.scraper._availability_cache = True
        self.scraper._cache_timestamp = datetime.now()
        
        result = await self.scraper.is_available()
        
        assert result is True
        # Should not call get_page due to cache
        self.mock_driver_manager.get_page.assert_not_called()
    
    def test_is_cache_valid_no_cache(self):
        """Test cache validity when no cache exists."""
        assert self.scraper._is_cache_valid() is False
    
    def test_is_cache_valid_expired(self):
        """Test cache validity when cache is expired."""
        from datetime import timedelta
        
        self.scraper._availability_cache = True
        self.scraper._cache_timestamp = datetime.now() - timedelta(seconds=400)
        
        assert self.scraper._is_cache_valid() is False
    
    def test_is_cache_valid_fresh(self):
        """Test cache validity when cache is fresh."""
        self.scraper._availability_cache = True
        self.scraper._cache_timestamp = datetime.now()
        
        assert self.scraper._is_cache_valid() is True
    
    @pytest.mark.asyncio
    async def test_ensure_logged_in_no_login_required(self):
        """Test ensure logged in when login not required."""
        scraper = JavDBScraper(
            driver_manager=self.mock_driver_manager,
            use_login=False
        )
        
        result = await scraper._ensure_logged_in()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ensure_logged_in_already_logged_in(self):
        """Test ensure logged in when already logged in."""
        self.mock_login_manager.is_logged_in.return_value = True
        
        result = await self.scraper._ensure_logged_in()
        
        assert result is True
        self.mock_login_manager.login.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ensure_logged_in_login_success(self):
        """Test ensure logged in with successful login."""
        self.mock_login_manager.is_logged_in.return_value = False
        self.mock_login_manager.login.return_value = True
        
        result = await self.scraper._ensure_logged_in()
        
        assert result is True
        self.mock_login_manager.login.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_logged_in_login_failure(self):
        """Test ensure logged in with login failure."""
        self.mock_login_manager.is_logged_in.return_value = False
        self.mock_login_manager.login.return_value = False
        
        result = await self.scraper._ensure_logged_in()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limit(self):
        """Test rate limiting functionality."""
        import time
        
        # Set last request time to now
        self.scraper._last_request_time = time.time()
        self.scraper._request_delay = 0.1  # Short delay for testing
        
        start_time = time.time()
        await self.scraper._rate_limit()
        elapsed = time.time() - start_time
        
        # Should have waited approximately the delay time
        assert elapsed >= 0.09  # Allow for small timing variations
    
    def test_parse_search_result_item_valid(self):
        """Test parsing valid search result item."""
        html = """
        <div class="item">
            <a href="/v/abc123">
                <img src="/thumb.jpg" alt="thumbnail">
                <div class="video-title">
                    <strong>ABC-123 Test Movie</strong>
                </div>
            </a>
            <div class="meta">2024-01-01</div>
        </div>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item')
        
        result = self.scraper._parse_search_result_item(item)
        
        assert result is not None
        assert result['url'] == "https://javdb.com/v/abc123"
        assert result['title'] == "ABC-123 Test Movie"
        assert result['code'] == "ABC-123"
        assert result['thumbnail'] == "https://javdb.com/thumb.jpg"
        assert result['meta'] == "2024-01-01"
    
    def test_parse_search_result_item_no_link(self):
        """Test parsing search result item without link."""
        html = """
        <div class="item">
            <div class="video-title">
                <strong>Test Movie</strong>
            </div>
        </div>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        item = soup.find('div', class_='item')
        
        result = self.scraper._parse_search_result_item(item)
        
        assert result is None
    
    def test_find_best_match_exact_match(self):
        """Test finding best match with exact code match."""
        results = [
            {'code': 'ABC-123', 'title': 'ABC-123 Movie', 'url': 'url1'},
            {'code': 'DEF-456', 'title': 'DEF-456 Movie', 'url': 'url2'},
        ]
        
        best_match = self.scraper._find_best_match(results, 'ABC-123')
        
        assert best_match['code'] == 'ABC-123'
    
    def test_find_best_match_partial_match(self):
        """Test finding best match with partial match."""
        results = [
            {'code': 'ABC123', 'title': 'ABC123 Movie', 'url': 'url1'},
            {'code': 'DEF-456', 'title': 'DEF-456 Movie', 'url': 'url2'},
        ]
        
        best_match = self.scraper._find_best_match(results, 'ABC-123')
        
        assert best_match['code'] == 'ABC123'
    
    def test_find_best_match_title_match(self):
        """Test finding best match with title containing code."""
        results = [
            {'code': '', 'title': 'Some ABC-123 Movie Title', 'url': 'url1'},
            {'code': 'DEF-456', 'title': 'DEF-456 Movie', 'url': 'url2'},
        ]
        
        best_match = self.scraper._find_best_match(results, 'ABC-123')
        
        assert 'ABC-123' in best_match['title'].upper()
    
    def test_find_best_match_no_match(self):
        """Test finding best match when no good matches."""
        results = [
            {'code': 'XYZ-999', 'title': 'XYZ-999 Movie', 'url': 'url1'},
        ]
        
        best_match = self.scraper._find_best_match(results, 'ABC-123')
        
        # Should return first result when no good matches
        assert best_match == results[0]
    
    def test_find_best_match_empty_results(self):
        """Test finding best match with empty results."""
        best_match = self.scraper._find_best_match([], 'ABC-123')
        
        assert best_match is None
    
    def test_extract_title(self):
        """Test title extraction."""
        html = """
        <html>
            <h2 class="title">Test Movie Title</h2>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        title = self.scraper._extract_title(soup)
        
        assert title == "Test Movie Title"
    
    def test_extract_title_not_found(self):
        """Test title extraction when not found."""
        html = "<html><body>No title here</body></html>"
        
        soup = BeautifulSoup(html, 'html.parser')
        title = self.scraper._extract_title(soup)
        
        assert title is None
    
    def test_extract_actresses(self):
        """Test actress extraction."""
        html = """
        <html>
            <a href="/actors/actress1">Actress One</a>
            <a href="/actors/actress2">Actress Two</a>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        actresses = self.scraper._extract_actresses(soup)
        
        assert len(actresses) == 2
        assert "Actress One" in actresses
        assert "Actress Two" in actresses
    
    def test_extract_actresses_duplicates(self):
        """Test actress extraction removes duplicates."""
        html = """
        <html>
            <a href="/actors/actress1">Actress One</a>
            <a href="/actors/actress1">Actress One</a>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        actresses = self.scraper._extract_actresses(soup)
        
        assert len(actresses) == 1
        assert actresses[0] == "Actress One"
    
    def test_extract_release_date(self):
        """Test release date extraction."""
        html = """
        <html>
            <body>Release Date: 2024-01-15</body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        release_date = self.scraper._extract_release_date(soup)
        
        assert release_date == date(2024, 1, 15)
    
    def test_extract_release_date_different_format(self):
        """Test release date extraction with different format."""
        html = """
        <html>
            <body>Date: 2024/01/15</body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        release_date = self.scraper._extract_release_date(soup)
        
        assert release_date == date(2024, 1, 15)
    
    def test_extract_release_date_not_found(self):
        """Test release date extraction when not found."""
        html = "<html><body>No date here</body></html>"
        
        soup = BeautifulSoup(html, 'html.parser')
        release_date = self.scraper._extract_release_date(soup)
        
        assert release_date is None
    
    def test_extract_duration(self):
        """Test duration extraction."""
        html = """
        <html>
            <body>Duration: 120分</body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        duration = self.scraper._extract_duration(soup)
        
        assert duration == 120
    
    def test_extract_duration_english(self):
        """Test duration extraction in English."""
        html = """
        <html>
            <body>Runtime: 90 minutes</body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        duration = self.scraper._extract_duration(soup)
        
        assert duration == 90
    
    def test_extract_duration_not_found(self):
        """Test duration extraction when not found."""
        html = "<html><body>No duration here</body></html>"
        
        soup = BeautifulSoup(html, 'html.parser')
        duration = self.scraper._extract_duration(soup)
        
        assert duration is None
    
    def test_extract_studio(self):
        """Test studio extraction."""
        html = """
        <html>
            <a href="/makers/studio1">Test Studio</a>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        studio = self.scraper._extract_studio(soup)
        
        assert studio == "Test Studio"
    
    def test_extract_genres(self):
        """Test genre extraction."""
        html = """
        <html>
            <a href="/tags/genre1">Action</a>
            <a href="/tags/genre2">Drama</a>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        genres = self.scraper._extract_genres(soup)
        
        assert len(genres) == 2
        assert "Action" in genres
        assert "Drama" in genres
    
    def test_extract_rating(self):
        """Test rating extraction."""
        html = """
        <html>
            <body>Rating: 8.5/10</body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        rating = self.scraper._extract_rating(soup)
        
        assert rating == 8.5
    
    def test_extract_rating_five_scale(self):
        """Test rating extraction on 5-point scale."""
        html = """
        <html>
            <body>Rating: 4.2/5</body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        rating = self.scraper._extract_rating(soup)
        
        assert rating == 8.4  # 4.2 * 2
    
    def test_extract_cover_image(self):
        """Test cover image extraction."""
        html = """
        <html>
            <div class="movie-poster">
                <img src="/cover.jpg" alt="cover">
            </div>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        cover_url = self.scraper._extract_cover_image(soup)
        
        assert cover_url == "https://javdb.com/cover.jpg"
    
    def test_extract_cover_image_full_url(self):
        """Test cover image extraction with full URL."""
        html = """
        <html>
            <div class="movie-poster">
                <img src="https://example.com/cover.jpg" alt="cover">
            </div>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        cover_url = self.scraper._extract_cover_image(soup)
        
        assert cover_url == "https://example.com/cover.jpg"
    
    def test_extract_screenshots(self):
        """Test screenshot extraction."""
        html = """
        <html>
            <div class="preview-images">
                <img src="/sample1.jpg" alt="sample">
                <img src="/sample2.jpg" alt="sample">
            </div>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        screenshots = self.scraper._extract_screenshots(soup)
        
        assert len(screenshots) == 2
        assert "https://javdb.com/sample1.jpg" in screenshots
        assert "https://javdb.com/sample2.jpg" in screenshots
    
    def test_extract_screenshots_no_duplicates(self):
        """Test screenshot extraction removes duplicates."""
        html = """
        <html>
            <div class="preview-images">
                <img src="/sample1.jpg" alt="sample">
                <img src="/sample1.jpg" alt="sample">
            </div>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        screenshots = self.scraper._extract_screenshots(soup)
        
        assert len(screenshots) == 1
        assert screenshots[0] == "https://javdb.com/sample1.jpg"
    
    @pytest.mark.asyncio
    async def test_search_movie_not_available(self):
        """Test search movie when JavDB not available."""
        with patch.object(self.scraper, 'is_available', return_value=False):
            result = await self.scraper.search_movie('ABC-123')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_movie_no_results(self):
        """Test search movie when no results found."""
        with patch.object(self.scraper, 'is_available', return_value=True):
            with patch.object(self.scraper, '_ensure_logged_in', return_value=True):
                with patch.object(self.scraper, '_search_by_code', return_value=[]):
                    result = await self.scraper.search_movie('ABC-123')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_movie_success(self):
        """Test successful movie search."""
        mock_search_results = [
            {'code': 'ABC-123', 'title': 'Test Movie', 'url': 'https://javdb.com/v/123'}
        ]
        
        mock_metadata = MovieMetadata(
            code='ABC-123',
            title='Test Movie',
            source_url='https://javdb.com/v/123'
        )
        
        with patch.object(self.scraper, 'is_available', return_value=True):
            with patch.object(self.scraper, '_ensure_logged_in', return_value=True):
                with patch.object(self.scraper, '_search_by_code', return_value=mock_search_results):
                    with patch.object(self.scraper, '_extract_movie_metadata', return_value=mock_metadata):
                        result = await self.scraper.search_movie('ABC-123')
        
        assert result is not None
        assert result.code == 'ABC-123'
        assert result.title == 'Test Movie'