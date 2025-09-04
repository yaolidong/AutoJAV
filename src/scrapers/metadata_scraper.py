"""Metadata scraper coordinator that manages multiple scrapers with priority and failover."""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from .base_scraper import BaseScraper
from ..models.movie_metadata import MovieMetadata


class MetadataScraper:
    """
    Coordinates multiple scrapers with priority-based failover and resource management.
    
    This class manages a collection of scrapers, attempting to fetch metadata
    from them in priority order with concurrent processing and intelligent
    failover mechanisms.
    """
    
    def __init__(
        self,
        scrapers: List[BaseScraper],
        max_concurrent_requests: int = 3,
        timeout_seconds: int = 60,
        retry_attempts: int = 2,
        cache_duration_minutes: int = 60
    ):
        """
        Initialize the metadata scraper coordinator.
        
        Args:
            scrapers: List of scraper instances in priority order
            max_concurrent_requests: Maximum concurrent scraping requests
            timeout_seconds: Timeout for individual scraper requests
            retry_attempts: Number of retry attempts for failed requests
            cache_duration_minutes: Duration to cache results
        """
        self.scrapers = scrapers
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        
        self.logger = logging.getLogger(__name__)
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_requests)
        
        # Cache for successful results
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        
        # Scraper availability tracking
        self._scraper_availability: Dict[str, Dict[str, Any]] = {}
        self._availability_check_interval = timedelta(minutes=5)
        
        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'scraper_usage': {scraper.name: 0 for scraper in scrapers}
        }
        
        self.logger.info(f"Initialized MetadataScraper with {len(scrapers)} scrapers")
    
    async def scrape_metadata(self, code: str, preferred_scrapers: Optional[List[str]] = None) -> Optional[MovieMetadata]:
        """
        Scrape metadata for a movie code using available scrapers.
        
        Args:
            code: Movie code to search for
            preferred_scrapers: Optional list of preferred scraper names to try first
            
        Returns:
            MovieMetadata if found, None otherwise
        """
        self.stats['total_requests'] += 1
        
        # Check cache first
        cached_result = self._get_cached_result(code)
        if cached_result:
            self.stats['cache_hits'] += 1
            self.logger.debug(f"Cache hit for code: {code}")
            return cached_result
        
        self.logger.info(f"Scraping metadata for code: {code}")
        
        # Get available scrapers in priority order
        available_scrapers = await self._get_available_scrapers(preferred_scrapers)
        
        if not available_scrapers:
            self.logger.error("No available scrapers found")
            self.stats['failed_requests'] += 1
            return None
        
        # Try scrapers in priority order
        for scraper in available_scrapers:
            try:
                self.logger.debug(f"Trying scraper: {scraper.name}")
                
                metadata = await self._scrape_with_timeout(scraper, code)
                
                if metadata:
                    self.logger.info(f"Successfully scraped metadata for {code} using {scraper.name}")
                    
                    # Cache the result
                    self._cache_result(code, metadata)
                    
                    # Update statistics
                    self.stats['successful_requests'] += 1
                    self.stats['scraper_usage'][scraper.name] += 1
                    
                    return metadata
                else:
                    self.logger.debug(f"No metadata found for {code} using {scraper.name}")
                    
            except Exception as e:
                self.logger.warning(f"Error using scraper {scraper.name} for {code}: {e}")
                # Mark scraper as temporarily unavailable
                self._mark_scraper_unavailable(scraper.name, str(e))
                continue
        
        # All scrapers failed
        self.logger.warning(f"Failed to scrape metadata for {code} using all available scrapers")
        self.stats['failed_requests'] += 1
        return None
    
    async def scrape_multiple(
        self,
        codes: List[str],
        max_concurrent: Optional[int] = None
    ) -> Dict[str, Optional[MovieMetadata]]:
        """
        Scrape metadata for multiple codes concurrently.
        
        Args:
            codes: List of movie codes to scrape
            max_concurrent: Override default concurrent limit
            
        Returns:
            Dictionary mapping codes to their metadata (or None if failed)
        """
        if not codes:
            return {}
        
        concurrent_limit = max_concurrent or self.max_concurrent_requests
        self.logger.info(f"Scraping metadata for {len(codes)} codes with {concurrent_limit} concurrent requests")
        
        results = {}
        
        # Process codes in batches to respect concurrency limits
        for i in range(0, len(codes), concurrent_limit):
            batch = codes[i:i + concurrent_limit]
            
            # Create tasks for the batch
            tasks = [self.scrape_metadata(code) for code in batch]
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process batch results
            for code, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Exception scraping {code}: {result}")
                    results[code] = None
                else:
                    results[code] = result
        
        successful_count = sum(1 for r in results.values() if r is not None)
        self.logger.info(f"Completed batch scraping: {successful_count}/{len(codes)} successful")
        
        return results
    
    async def _scrape_with_timeout(self, scraper: BaseScraper, code: str) -> Optional[MovieMetadata]:
        """
        Scrape metadata with timeout and retry logic.
        
        Args:
            scraper: Scraper instance to use
            code: Movie code to search for
            
        Returns:
            MovieMetadata if successful, None otherwise
        """
        for attempt in range(self.retry_attempts + 1):
            try:
                # Use asyncio.wait_for to enforce timeout
                metadata = await asyncio.wait_for(
                    scraper.search_movie(code),
                    timeout=self.timeout_seconds
                )
                
                if metadata:
                    return metadata
                    
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout scraping {code} with {scraper.name} (attempt {attempt + 1})")
                if attempt < self.retry_attempts:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    
            except Exception as e:
                self.logger.warning(f"Error scraping {code} with {scraper.name} (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
        
        return None
    
    async def _get_available_scrapers(self, preferred_scrapers: Optional[List[str]] = None) -> List[BaseScraper]:
        """
        Get list of available scrapers in priority order.
        
        Args:
            preferred_scrapers: Optional list of preferred scraper names
            
        Returns:
            List of available scrapers in priority order
        """
        available_scrapers = []
        
        # Check scraper availability
        availability_tasks = []
        for scraper in self.scrapers:
            if self._should_check_availability(scraper.name):
                availability_tasks.append(self._check_scraper_availability(scraper))
        
        if availability_tasks:
            await asyncio.gather(*availability_tasks, return_exceptions=True)
        
        # Build priority list
        scraper_priority = []
        
        # Add preferred scrapers first (if specified and available)
        if preferred_scrapers:
            for name in preferred_scrapers:
                scraper = self._get_scraper_by_name(name)
                if scraper and self._is_scraper_available(name):
                    scraper_priority.append(scraper)
        
        # Add remaining scrapers in original order
        for scraper in self.scrapers:
            if scraper not in scraper_priority and self._is_scraper_available(scraper.name):
                scraper_priority.append(scraper)
        
        return scraper_priority
    
    async def _check_scraper_availability(self, scraper: BaseScraper) -> None:
        """
        Check and update scraper availability status.
        
        Args:
            scraper: Scraper instance to check
        """
        try:
            is_available = await asyncio.wait_for(
                scraper.is_available(),
                timeout=10  # Short timeout for availability checks
            )
            
            self._scraper_availability[scraper.name] = {
                'available': is_available,
                'last_check': datetime.now(),
                'error': None
            }
            
            self.logger.debug(f"Scraper {scraper.name} availability: {is_available}")
            
        except Exception as e:
            self.logger.warning(f"Error checking availability for {scraper.name}: {e}")
            self._scraper_availability[scraper.name] = {
                'available': False,
                'last_check': datetime.now(),
                'error': str(e)
            }
    
    def _should_check_availability(self, scraper_name: str) -> bool:
        """
        Determine if scraper availability should be checked.
        
        Args:
            scraper_name: Name of the scraper
            
        Returns:
            True if availability check is needed
        """
        if scraper_name not in self._scraper_availability:
            return True
        
        last_check = self._scraper_availability[scraper_name].get('last_check')
        if not last_check:
            return True
        
        return datetime.now() - last_check > self._availability_check_interval
    
    def _is_scraper_available(self, scraper_name: str) -> bool:
        """
        Check if scraper is currently available.
        
        Args:
            scraper_name: Name of the scraper
            
        Returns:
            True if scraper is available
        """
        if scraper_name not in self._scraper_availability:
            return True  # Assume available if not checked yet
        
        return self._scraper_availability[scraper_name].get('available', True)
    
    def _mark_scraper_unavailable(self, scraper_name: str, error: str) -> None:
        """
        Mark scraper as temporarily unavailable.
        
        Args:
            scraper_name: Name of the scraper
            error: Error message
        """
        self._scraper_availability[scraper_name] = {
            'available': False,
            'last_check': datetime.now(),
            'error': error
        }
        
        self.logger.warning(f"Marked scraper {scraper_name} as unavailable: {error}")
    
    def _get_scraper_by_name(self, name: str) -> Optional[BaseScraper]:
        """
        Get scraper instance by name.
        
        Args:
            name: Scraper name
            
        Returns:
            Scraper instance if found, None otherwise
        """
        for scraper in self.scrapers:
            if scraper.name == name:
                return scraper
        return None
    
    def _get_cached_result(self, code: str) -> Optional[MovieMetadata]:
        """
        Get cached metadata result if available and not expired.
        
        Args:
            code: Movie code
            
        Returns:
            Cached MovieMetadata if available, None otherwise
        """
        if code not in self._metadata_cache:
            return None
        
        cache_entry = self._metadata_cache[code]
        cached_time = cache_entry.get('timestamp')
        
        if not cached_time or datetime.now() - cached_time > self.cache_duration:
            # Cache expired
            del self._metadata_cache[code]
            return None
        
        return cache_entry.get('metadata')
    
    def _cache_result(self, code: str, metadata: MovieMetadata) -> None:
        """
        Cache metadata result.
        
        Args:
            code: Movie code
            metadata: Metadata to cache
        """
        self._metadata_cache[code] = {
            'metadata': metadata,
            'timestamp': datetime.now()
        }
        
        # Limit cache size (simple LRU-like behavior)
        if len(self._metadata_cache) > 1000:
            # Remove oldest entries
            sorted_entries = sorted(
                self._metadata_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            # Keep newest 800 entries
            self._metadata_cache = dict(sorted_entries[-800:])
    
    def get_available_scrapers(self) -> List[str]:
        """
        Get list of available scraper names.
        
        Returns:
            List of available scraper names
        """
        return [
            scraper.name for scraper in self.scrapers
            if self._is_scraper_available(scraper.name)
        ]
    
    def get_scraper_stats(self) -> Dict[str, Any]:
        """
        Get scraper usage statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_requests': self.stats['total_requests'],
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'success_rate': (
                self.stats['successful_requests'] / max(1, self.stats['total_requests'])
            ) * 100,
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(1, self.stats['total_requests'])
            ) * 100,
            'scraper_usage': self.stats['scraper_usage'].copy(),
            'scraper_availability': {
                name: info.get('available', True)
                for name, info in self._scraper_availability.items()
            }
        }
    
    def clear_cache(self) -> None:
        """Clear the metadata cache."""
        self._metadata_cache.clear()
        self.logger.info("Metadata cache cleared")
    
    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'scraper_usage': {scraper.name: 0 for scraper in self.scrapers}
        }
        self.logger.info("Statistics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all scrapers.
        
        Returns:
            Dictionary with health status of all scrapers
        """
        self.logger.info("Performing health check on all scrapers")
        
        health_status = {}
        
        # Check all scrapers concurrently
        tasks = [self._check_scraper_availability(scraper) for scraper in self.scrapers]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile health status
        for scraper in self.scrapers:
            availability_info = self._scraper_availability.get(scraper.name, {})
            health_status[scraper.name] = {
                'available': availability_info.get('available', False),
                'last_check': availability_info.get('last_check'),
                'error': availability_info.get('error'),
                'usage_count': self.stats['scraper_usage'].get(scraper.name, 0)
            }
        
        return health_status
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

    async def cleanup(self):
        """Clean up resources used by all scrapers."""
        self.logger.info("Cleaning up all scraper resources...")
        for scraper in self.scrapers:
            if hasattr(scraper, 'cleanup') and asyncio.iscoroutinefunction(scraper.cleanup):
                await scraper.cleanup()
            elif hasattr(scraper, 'cleanup'):
                scraper.cleanup()