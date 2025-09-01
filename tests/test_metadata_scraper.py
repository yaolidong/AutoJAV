"""Tests for MetadataScraper coordinator."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, date

from src.scrapers.metadata_scraper import MetadataScraper
from src.scrapers.base_scraper import BaseScraper
from src.models.movie_metadata import MovieMetadata


class MockScraper(BaseScraper):
    """Mock scraper for testing."""
    
    def __init__(self, name: str, available: bool = True, should_fail: bool = False):
        super().__init__(name)
        self._available = available
        self.should_fail = should_fail
        self.search_calls = []
    
    async def search_movie(self, code: str) -> MovieMetadata:
        """Mock search implementation."""
        self.search_calls.append(code)
        
        if self.should_fail:
            raise Exception(f"Mock error from {self.name}")
        
        if not self._available:
            return None
        
        # Return mock metadata
        return MovieMetadata(
            code=code,
            title=f"Test Movie {code}",
            actresses=[f"Actress from {self.name}"],
            source_url=f"https://{self.name}.com/movie/{code}"
        )
    
    async def is_available(self) -> bool:
        """Mock availability check."""
        return self._available


class TestMetadataScraper:
    """Test cases for MetadataScraper."""
    
    @pytest.fixture
    def mock_scrapers(self):
        """Create mock scrapers for testing."""
        return [
            MockScraper("javdb", available=True),
            MockScraper("javlibrary", available=True),
            MockScraper("unavailable", available=False)
        ]
    
    @pytest.fixture
    def metadata_scraper(self, mock_scrapers):
        """Create MetadataScraper instance."""
        return MetadataScraper(
            scrapers=mock_scrapers,
            max_concurrent_requests=2,
            timeout_seconds=5,
            retry_attempts=1,
            cache_duration_minutes=1
        )
    
    def test_init(self, mock_scrapers):
        """Test MetadataScraper initialization."""
        scraper = MetadataScraper(mock_scrapers)
        
        assert len(scraper.scrapers) == 3
        assert scraper.max_concurrent_requests == 3  # default
        assert scraper.timeout_seconds == 60  # default
        assert scraper.retry_attempts == 2  # default
        assert len(scraper.stats['scraper_usage']) == 3
    
    def test_init_custom_params(self, mock_scrapers):
        """Test MetadataScraper initialization with custom parameters."""
        scraper = MetadataScraper(
            scrapers=mock_scrapers,
            max_concurrent_requests=5,
            timeout_seconds=30,
            retry_attempts=3,
            cache_duration_minutes=120
        )
        
        assert scraper.max_concurrent_requests == 5
        assert scraper.timeout_seconds == 30
        assert scraper.retry_attempts == 3
        assert scraper.cache_duration == timedelta(minutes=120)
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_success_first_scraper(self, metadata_scraper):
        """Test successful metadata scraping with first scraper."""
        result = await metadata_scraper.scrape_metadata("SSIS-001")
        
        assert result is not None
        assert result.code == "SSIS-001"
        assert result.title == "Test Movie SSIS-001"
        assert "javdb" in result.source_url
        
        # Check statistics
        assert metadata_scraper.stats['total_requests'] == 1
        assert metadata_scraper.stats['successful_requests'] == 1
        assert metadata_scraper.stats['failed_requests'] == 0
        assert metadata_scraper.stats['scraper_usage']['javdb'] == 1
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_failover(self, metadata_scraper):
        """Test failover to second scraper when first fails."""
        # Make first scraper fail
        metadata_scraper.scrapers[0].should_fail = True
        
        result = await metadata_scraper.scrape_metadata("SSIS-002")
        
        assert result is not None
        assert result.code == "SSIS-002"
        assert "javlibrary" in result.source_url
        
        # Check that both scrapers were tried
        assert metadata_scraper.scrapers[0].search_calls == ["SSIS-002"]
        assert metadata_scraper.scrapers[1].search_calls == ["SSIS-002"]
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_all_fail(self, metadata_scraper):
        """Test when all scrapers fail."""
        # Make all scrapers fail
        for scraper in metadata_scraper.scrapers:
            scraper.should_fail = True
        
        result = await metadata_scraper.scrape_metadata("SSIS-003")
        
        assert result is None
        assert metadata_scraper.stats['failed_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_no_available_scrapers(self, metadata_scraper):
        """Test when no scrapers are available."""
        # Make all scrapers unavailable
        for scraper in metadata_scraper.scrapers:
            scraper._available = False
        
        result = await metadata_scraper.scrape_metadata("SSIS-004")
        
        assert result is None
        assert metadata_scraper.stats['failed_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_with_preferred_scrapers(self, metadata_scraper):
        """Test scraping with preferred scraper list."""
        # Prefer javlibrary over javdb
        result = await metadata_scraper.scrape_metadata(
            "SSIS-005",
            preferred_scrapers=["javlibrary", "javdb"]
        )
        
        assert result is not None
        assert "javlibrary" in result.source_url
        
        # javlibrary should be called first
        assert metadata_scraper.scrapers[1].search_calls == ["SSIS-005"]
        assert metadata_scraper.scrapers[0].search_calls == []
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_caching(self, metadata_scraper):
        """Test metadata caching functionality."""
        # First request
        result1 = await metadata_scraper.scrape_metadata("SSIS-006")
        assert result1 is not None
        
        # Second request should use cache
        result2 = await metadata_scraper.scrape_metadata("SSIS-006")
        assert result2 is not None
        assert result1.code == result2.code
        
        # Check cache hit statistics
        assert metadata_scraper.stats['cache_hits'] == 1
        assert metadata_scraper.stats['total_requests'] == 2
        
        # Scraper should only be called once
        assert len(metadata_scraper.scrapers[0].search_calls) == 1
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_cache_expiry(self, metadata_scraper):
        """Test cache expiry functionality."""
        # Set very short cache duration
        metadata_scraper.cache_duration = timedelta(milliseconds=1)
        
        # First request
        result1 = await metadata_scraper.scrape_metadata("SSIS-007")
        assert result1 is not None
        
        # Wait for cache to expire
        await asyncio.sleep(0.002)
        
        # Second request should not use cache
        result2 = await metadata_scraper.scrape_metadata("SSIS-007")
        assert result2 is not None
        
        # No cache hits
        assert metadata_scraper.stats['cache_hits'] == 0
        
        # Scraper should be called twice
        assert len(metadata_scraper.scrapers[0].search_calls) == 2
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_success(self, metadata_scraper):
        """Test scraping multiple codes successfully."""
        codes = ["SSIS-008", "SSIS-009", "SSIS-010"]
        
        results = await metadata_scraper.scrape_multiple(codes)
        
        assert len(results) == 3
        for code in codes:
            assert results[code] is not None
            assert results[code].code == code
        
        assert metadata_scraper.stats['successful_requests'] == 3
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_mixed_results(self, metadata_scraper):
        """Test scraping multiple codes with mixed success/failure."""
        codes = ["SSIS-011", "FAIL-001", "SSIS-012"]
        
        # Make second scraper fail for specific code
        original_search = metadata_scraper.scrapers[0].search_movie
        
        async def mock_search(code):
            if code == "FAIL-001":
                raise Exception("Mock failure")
            return await original_search(code)
        
        metadata_scraper.scrapers[0].search_movie = mock_search
        
        results = await metadata_scraper.scrape_multiple(codes)
        
        assert len(results) == 3
        assert results["SSIS-011"] is not None
        assert results["FAIL-001"] is None  # Should fail
        assert results["SSIS-012"] is not None
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_empty_list(self, metadata_scraper):
        """Test scraping empty code list."""
        results = await metadata_scraper.scrape_multiple([])
        
        assert results == {}
        assert metadata_scraper.stats['total_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_with_concurrency_limit(self, metadata_scraper):
        """Test scraping multiple codes with custom concurrency limit."""
        codes = ["SSIS-013", "SSIS-014", "SSIS-015", "SSIS-016"]
        
        results = await metadata_scraper.scrape_multiple(codes, max_concurrent=1)
        
        assert len(results) == 4
        for code in codes:
            assert results[code] is not None
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, metadata_scraper):
        """Test timeout handling in scraper requests."""
        # Create a scraper that takes too long
        slow_scraper = MockScraper("slow")
        
        async def slow_search(code):
            await asyncio.sleep(10)  # Longer than timeout
            return MovieMetadata(code=code, title="Slow result")
        
        slow_scraper.search_movie = slow_search
        metadata_scraper.scrapers.insert(0, slow_scraper)
        
        # Should timeout and try next scraper
        result = await metadata_scraper.scrape_metadata("SSIS-017")
        
        assert result is not None
        assert "javdb" in result.source_url  # Should use second scraper
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, metadata_scraper):
        """Test retry mechanism for failed requests."""
        # Create scraper that fails first time, succeeds second time
        retry_scraper = MockScraper("retry")
        call_count = 0
        
        async def flaky_search(code):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return MovieMetadata(code=code, title="Retry success")
        
        retry_scraper.search_movie = flaky_search
        metadata_scraper.scrapers = [retry_scraper]
        
        result = await metadata_scraper.scrape_metadata("SSIS-018")
        
        assert result is not None
        assert result.title == "Retry success"
        assert call_count == 2  # Should retry once
    
    def test_get_available_scrapers(self, metadata_scraper):
        """Test getting list of available scrapers."""
        # Initially all should be available (except the unavailable one)
        available = metadata_scraper.get_available_scrapers()
        
        # Should include available scrapers
        assert "javdb" in available
        assert "javlibrary" in available
        # May or may not include "unavailable" depending on when availability was checked
    
    def test_get_scraper_stats(self, metadata_scraper):
        """Test getting scraper statistics."""
        stats = metadata_scraper.get_scraper_stats()
        
        assert 'total_requests' in stats
        assert 'successful_requests' in stats
        assert 'failed_requests' in stats
        assert 'success_rate' in stats
        assert 'cache_hits' in stats
        assert 'cache_hit_rate' in stats
        assert 'scraper_usage' in stats
        assert 'scraper_availability' in stats
        
        # Check initial values
        assert stats['total_requests'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['cache_hit_rate'] == 0.0
    
    def test_clear_cache(self, metadata_scraper):
        """Test cache clearing functionality."""
        # Add something to cache
        metadata_scraper._cache_result("TEST-001", MovieMetadata(code="TEST-001", title="Test"))
        
        assert len(metadata_scraper._metadata_cache) == 1
        
        metadata_scraper.clear_cache()
        
        assert len(metadata_scraper._metadata_cache) == 0
    
    def test_reset_stats(self, metadata_scraper):
        """Test statistics reset functionality."""
        # Modify stats
        metadata_scraper.stats['total_requests'] = 10
        metadata_scraper.stats['successful_requests'] = 8
        
        metadata_scraper.reset_stats()
        
        assert metadata_scraper.stats['total_requests'] == 0
        assert metadata_scraper.stats['successful_requests'] == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, metadata_scraper):
        """Test health check functionality."""
        health_status = await metadata_scraper.health_check()
        
        assert isinstance(health_status, dict)
        assert len(health_status) == len(metadata_scraper.scrapers)
        
        for scraper_name in ["javdb", "javlibrary", "unavailable"]:
            assert scraper_name in health_status
            status = health_status[scraper_name]
            assert 'available' in status
            assert 'last_check' in status
            assert 'error' in status
            assert 'usage_count' in status
    
    def test_get_scraper_by_name(self, metadata_scraper):
        """Test getting scraper by name."""
        scraper = metadata_scraper._get_scraper_by_name("javdb")
        assert scraper is not None
        assert scraper.name == "javdb"
        
        scraper = metadata_scraper._get_scraper_by_name("nonexistent")
        assert scraper is None
    
    def test_cache_size_limit(self, metadata_scraper):
        """Test cache size limiting functionality."""
        # Add many entries to cache
        for i in range(1200):  # More than the 1000 limit
            code = f"TEST-{i:04d}"
            metadata = MovieMetadata(code=code, title=f"Test {i}")
            metadata_scraper._cache_result(code, metadata)
        
        # Cache should be limited to 800 entries (after cleanup)
        assert len(metadata_scraper._metadata_cache) == 800
        
        # Should keep the newest entries
        assert "TEST-1199" in metadata_scraper._metadata_cache
        assert "TEST-0000" not in metadata_scraper._metadata_cache
    
    def test_cache_expiry_check(self, metadata_scraper):
        """Test cache expiry checking."""
        code = "EXPIRE-TEST"
        metadata = MovieMetadata(code=code, title="Test")
        
        # Add to cache with current timestamp
        metadata_scraper._cache_result(code, metadata)
        
        # Should be available
        result = metadata_scraper._get_cached_result(code)
        assert result is not None
        
        # Manually expire the cache entry
        metadata_scraper._metadata_cache[code]['timestamp'] = (
            datetime.now() - timedelta(hours=2)
        )
        
        # Should be expired and removed
        result = metadata_scraper._get_cached_result(code)
        assert result is None
        assert code not in metadata_scraper._metadata_cache
    
    def test_mark_scraper_unavailable(self, metadata_scraper):
        """Test marking scraper as unavailable."""
        scraper_name = "javdb"
        error_msg = "Test error"
        
        metadata_scraper._mark_scraper_unavailable(scraper_name, error_msg)
        
        assert not metadata_scraper._is_scraper_available(scraper_name)
        assert metadata_scraper._scraper_availability[scraper_name]['error'] == error_msg
    
    def test_should_check_availability(self, metadata_scraper):
        """Test availability check timing logic."""
        scraper_name = "test_scraper"
        
        # Should check if never checked
        assert metadata_scraper._should_check_availability(scraper_name)
        
        # Add recent check
        metadata_scraper._scraper_availability[scraper_name] = {
            'last_check': datetime.now(),
            'available': True
        }
        
        # Should not check if recently checked
        assert not metadata_scraper._should_check_availability(scraper_name)
        
        # Should check if old
        metadata_scraper._scraper_availability[scraper_name]['last_check'] = (
            datetime.now() - timedelta(minutes=10)
        )
        
        assert metadata_scraper._should_check_availability(scraper_name)
    
    @pytest.mark.asyncio
    async def test_check_scraper_availability_success(self, metadata_scraper):
        """Test successful scraper availability check."""
        scraper = metadata_scraper.scrapers[0]  # javdb
        
        await metadata_scraper._check_scraper_availability(scraper)
        
        assert scraper.name in metadata_scraper._scraper_availability
        availability_info = metadata_scraper._scraper_availability[scraper.name]
        assert availability_info['available'] is True
        assert availability_info['error'] is None
        assert availability_info['last_check'] is not None
    
    @pytest.mark.asyncio
    async def test_check_scraper_availability_failure(self, metadata_scraper):
        """Test failed scraper availability check."""
        scraper = metadata_scraper.scrapers[0]  # javdb
        
        # Make availability check fail
        async def failing_check():
            raise Exception("Availability check failed")
        
        scraper.is_available = failing_check
        
        await metadata_scraper._check_scraper_availability(scraper)
        
        availability_info = metadata_scraper._scraper_availability[scraper.name]
        assert availability_info['available'] is False
        assert "Availability check failed" in availability_info['error']


if __name__ == "__main__":
    pytest.main([__file__])