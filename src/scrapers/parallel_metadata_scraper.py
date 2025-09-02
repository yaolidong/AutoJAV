"""
Enhanced Metadata Scraper with Parallel Querying and Result Merging
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..models.movie_metadata import MovieMetadata
from .base_scraper import BaseScraper


class ParallelMetadataScraper:
    """
    Enhanced metadata scraper that queries all sources in parallel
    and merges results for better success rate
    """
    
    def __init__(
        self,
        scrapers: List[BaseScraper],
        cache_duration_minutes: int = 60,
        parallel_timeout: int = 30
    ):
        """
        Initialize parallel metadata scraper.
        
        Args:
            scrapers: List of scrapers to use
            cache_duration_minutes: Cache duration in minutes
            parallel_timeout: Timeout for parallel queries in seconds
        """
        self.scrapers = scrapers
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.parallel_timeout = parallel_timeout
        self.logger = logging.getLogger(__name__)
        
        # Cache for results
        self.cache = {}
        self.cache_timestamps = {}
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'partial_success': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'scraper_success': {scraper.name: 0 for scraper in scrapers},
            'scraper_failures': {scraper.name: 0 for scraper in scrapers}
        }
        
        self.logger.info(f"Initialized ParallelMetadataScraper with {len(scrapers)} scrapers")
    
    async def scrape_metadata_parallel(self, code: str) -> Optional[MovieMetadata]:
        """
        Scrape metadata from all sources in parallel and merge results.
        
        Args:
            code: Movie code to search for
            
        Returns:
            Merged MovieMetadata if any source succeeds, None otherwise
        """
        self.stats['total_requests'] += 1
        
        # Check cache first
        cached_result = self._get_cached_result(code)
        if cached_result:
            self.stats['cache_hits'] += 1
            self.logger.debug(f"Cache hit for code: {code}")
            return cached_result
        
        self.logger.info(f"Parallel scraping metadata for code: {code}")
        
        # Create tasks for all scrapers
        tasks = []
        scraper_names = []
        
        for scraper in self.scrapers:
            task = self._scrape_with_timeout(scraper, code)
            tasks.append(task)
            scraper_names.append(scraper.name)
        
        # Run all scrapers in parallel
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.parallel_timeout
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"Parallel scraping timeout for {code}")
            results = []
        
        # Process results
        successful_results = []
        for i, result in enumerate(results):
            scraper_name = scraper_names[i] if i < len(scraper_names) else "unknown"
            
            if isinstance(result, Exception):
                self.logger.debug(f"Scraper {scraper_name} failed: {result}")
                self.stats['scraper_failures'][scraper_name] += 1
            elif result:
                self.logger.info(f"Scraper {scraper_name} succeeded for {code}")
                successful_results.append((scraper_name, result))
                self.stats['scraper_success'][scraper_name] += 1
            else:
                self.logger.debug(f"Scraper {scraper_name} returned no data for {code}")
                self.stats['scraper_failures'][scraper_name] += 1
        
        # Merge results if any succeeded
        if successful_results:
            merged_metadata = self._merge_metadata_results(successful_results)
            
            if merged_metadata:
                self.logger.info(f"Successfully scraped and merged metadata for {code} from {len(successful_results)} sources")
                
                # Cache the result
                self._cache_result(code, merged_metadata)
                
                # Update statistics
                if len(successful_results) == len(self.scrapers):
                    self.stats['successful_requests'] += 1
                else:
                    self.stats['partial_success'] += 1
                
                return merged_metadata
        
        # All scrapers failed
        self.logger.warning(f"All scrapers failed for {code}")
        self.stats['failed_requests'] += 1
        return None
    
    def _merge_metadata_results(self, results: List[tuple]) -> Optional[MovieMetadata]:
        """
        Merge metadata from multiple sources, prioritizing completeness.
        
        Args:
            results: List of (scraper_name, metadata) tuples
            
        Returns:
            Merged MovieMetadata
        """
        if not results:
            return None
        
        # Start with the first result
        base_name, base_metadata = results[0]
        
        if len(results) == 1:
            return base_metadata
        
        self.logger.debug(f"Merging {len(results)} metadata results")
        
        # Create a merged metadata object
        merged = MovieMetadata(
            code=base_metadata.code,
            title=base_metadata.title,
            actresses=base_metadata.actresses.copy() if base_metadata.actresses else [],
            release_date=base_metadata.release_date,
            studio=base_metadata.studio,
            director=base_metadata.director,
            duration=base_metadata.duration,
            series=base_metadata.series,
            genres=base_metadata.genres.copy() if base_metadata.genres else [],
            cover_url=base_metadata.cover_url,
            thumbnail_url=base_metadata.thumbnail_url,
            gallery_urls=base_metadata.gallery_urls.copy() if base_metadata.gallery_urls else [],
            score=base_metadata.score,
            description=base_metadata.description,
            source_urls=base_metadata.source_urls.copy() if base_metadata.source_urls else {}
        )
        
        # Add source information
        merged.source_urls[base_name] = merged.source_urls.get(base_name, "")
        
        # Merge data from other sources
        for scraper_name, metadata in results[1:]:
            # Merge actresses (union)
            if metadata.actresses:
                for actress in metadata.actresses:
                    if actress not in merged.actresses and actress != "未知女优":
                        merged.actresses.append(actress)
            
            # Use longer title
            if metadata.title and len(metadata.title) > len(merged.title or ""):
                merged.title = metadata.title
            
            # Use more complete studio info
            if not merged.studio and metadata.studio:
                merged.studio = metadata.studio
            
            # Use more complete director info
            if not merged.director and metadata.director:
                merged.director = metadata.director
            
            # Use longer duration
            if metadata.duration and (not merged.duration or metadata.duration > merged.duration):
                merged.duration = metadata.duration
            
            # Merge genres (union)
            if metadata.genres:
                for genre in metadata.genres:
                    if genre not in merged.genres:
                        merged.genres.append(genre)
            
            # Use higher resolution cover
            if metadata.cover_url and not merged.cover_url:
                merged.cover_url = metadata.cover_url
            
            # Collect all gallery URLs
            if metadata.gallery_urls:
                for url in metadata.gallery_urls:
                    if url not in merged.gallery_urls:
                        merged.gallery_urls.append(url)
            
            # Use higher score
            if metadata.score and (not merged.score or metadata.score > merged.score):
                merged.score = metadata.score
            
            # Use longer description
            if metadata.description and len(metadata.description or "") > len(merged.description or ""):
                merged.description = metadata.description
            
            # Add source URL
            if scraper_name:
                merged.source_urls[scraper_name] = metadata.source_urls.get(scraper_name, "")
        
        return merged
    
    async def _scrape_with_timeout(self, scraper: BaseScraper, code: str) -> Optional[MovieMetadata]:
        """
        Scrape with timeout for a single scraper.
        
        Args:
            scraper: Scraper to use
            code: Movie code
            
        Returns:
            MovieMetadata if successful, None otherwise
        """
        try:
            # All scrapers should have search_movie as async method
            if hasattr(scraper, 'search_movie'):
                return await scraper.search_movie(code)
            elif hasattr(scraper, 'scrape_async'):
                # Fallback for legacy scrapers
                return await scraper.scrape_async(code)
            else:
                # Run sync scraper in executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, scraper.scrape, code)
                
        except asyncio.TimeoutError:
            self.logger.warning(f"Scraper {scraper.name} timeout for {code}")
            return None
        except Exception as e:
            self.logger.error(f"Scraper {scraper.name} error for {code}: {e}")
            return None
    
    def _get_cached_result(self, code: str) -> Optional[MovieMetadata]:
        """Get cached result if still valid."""
        if code in self.cache:
            timestamp = self.cache_timestamps.get(code)
            if timestamp and (datetime.now() - timestamp) < self.cache_duration:
                return self.cache[code]
            else:
                # Cache expired
                del self.cache[code]
                del self.cache_timestamps[code]
        return None
    
    def _cache_result(self, code: str, metadata: MovieMetadata) -> None:
        """Cache the result."""
        self.cache[code] = metadata
        self.cache_timestamps[code] = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        return self.stats.copy()
    
    def clear_cache(self) -> None:
        """Clear the metadata cache."""
        self.cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("Metadata cache cleared")