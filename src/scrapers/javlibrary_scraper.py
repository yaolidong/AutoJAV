"""JavLibrary scraper for fetching movie metadata without login."""

import re
import logging
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, quote
from datetime import datetime, date

from bs4 import BeautifulSoup
import aiohttp

try:
    from .base_scraper import BaseScraper
    from ..models.movie_metadata import MovieMetadata
    from ..utils.http_client import HttpClient
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scrapers.base_scraper import BaseScraper
    from models.movie_metadata import MovieMetadata
    from utils.http_client import HttpClient


class JavLibraryScraper(BaseScraper):
    """Scraper for JavLibrary website (no login required)."""
    
    BASE_URL = "https://www.javlibrary.com"
    SEARCH_URL = f"{BASE_URL}/en/vl_searchbyid.php"
    
    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        language: str = "en"
    ):
        """
        Initialize JavLibrary scraper.
        
        Args:
            http_client: HTTP client instance for making requests
            language: Language preference ('en' or 'ja')
        """
        super().__init__("JavLibrary")
        self.http_client = http_client or HttpClient(
            timeout=30,
            rate_limit_delay=2.0,
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
        )
        self.language = language
        self.logger = logging.getLogger(__name__)
        
        # Cache for availability check
        self._availability_cache = None
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes
        
        # Update base URL for language
        if language == "ja":
            self.BASE_URL = "https://www.javlibrary.com/ja"
            self.SEARCH_URL = f"{self.BASE_URL}/vl_searchbyid.php"
    
    async def is_available(self) -> bool:
        """
        Check if JavLibrary is available and accessible.
        
        Returns:
            True if available, False otherwise
        """
        # Check cache first
        if self._is_cache_valid():
            return self._availability_cache
        
        try:
            self.logger.debug("Checking JavLibrary availability...")
            response = await self.http_client.get(self.BASE_URL)
            async with response:
                success = response.status == 200
                self._availability_cache = success
                self._cache_timestamp = datetime.now()
                self.logger.debug(f"JavLibrary availability: {success}")
                return success
                
        except Exception as e:
            self.logger.error(f"Error checking JavLibrary availability: {e}")
            self._availability_cache = False
            self._cache_timestamp = datetime.now()
            return False
    
    def _is_cache_valid(self) -> bool:
        """Check if availability cache is still valid."""
        if self._availability_cache is None or self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """
        Search for movie metadata by code.
        
        Args:
            code: Movie code to search for
            
        Returns:
            MovieMetadata if found, None otherwise
        """
        try:
            # Check availability
            if not await self.is_available():
                self.logger.error("JavLibrary is not available")
                return None
            
            self.logger.info(f"Searching JavLibrary for code: {code}")
            
            # Search for the movie
            movie_url = await self._search_by_code(code)
            
            if not movie_url:
                self.logger.info(f"No results found for code: {code}")
                return None
            
            # Extract detailed metadata
            metadata = await self._extract_movie_metadata(movie_url, code)
            
            if metadata:
                self.logger.info(f"Successfully scraped metadata for: {code}")
            else:
                self.logger.warning(f"Failed to extract metadata for: {code}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error searching for {code}: {e}")
            return None
    
    async def _search_by_code(self, code: str) -> Optional[str]:
        """
        Search JavLibrary by movie code and return the movie page URL.
        
        Args:
            code: Movie code to search for
            
        Returns:
            Movie page URL if found, None otherwise
        """
        try:
            # Clean the code for search
            search_code = self._clean_code_for_search(code)
            
            # Construct search URL
            search_params = {'keyword': search_code}
            
            self.logger.debug(f"Searching for code: {search_code}")
            
            response = await self.http_client.get(self.SEARCH_URL, params=search_params)
            async with response:
                if response.status != 200:
                    self.logger.error(f"Search request failed: {response.status}")
                    return None

                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                if 'vl_movie.php' in str(response.url):
                    return str(response.url)

                movie_url = self._parse_search_results(soup, code)

                if movie_url and not movie_url.startswith('http'):
                    movie_url = urljoin(self.BASE_URL, movie_url)

                return movie_url
                    
        except Exception as e:
            self.logger.error(f"Error searching by code {code}: {e}")
            return None
    
    def _clean_code_for_search(self, code: str) -> str:
        """
        Clean movie code for JavLibrary search.
        
        Args:
            code: Original movie code
            
        Returns:
            Cleaned code for search
        """
        # Remove common prefixes and clean format
        code = code.upper().strip()
        
        # Handle different code formats
        # Remove hyphens for search (JavLibrary often works better without them)
        search_code = re.sub(r'[-_\s]', '', code)
        
        return search_code
    
    def _parse_search_results(self, soup: BeautifulSoup, target_code: str) -> Optional[str]:
        """
        Parse search results page to find the best matching movie.
        
        Args:
            soup: BeautifulSoup object of search results page
            target_code: Target movie code
            
        Returns:
            Movie page URL if found, None otherwise
        """
        try:
            # Look for movie entries in search results
            movie_links = soup.find_all('a', href=re.compile(r'vl_movie\.php'))
            
            if not movie_links:
                self.logger.debug("No movie links found in search results")
                return None
            
            target_code_clean = re.sub(r'[^A-Z0-9]', '', target_code.upper())
            
            # Score each result to find the best match
            best_match = None
            best_score = 0
            
            for link in movie_links:
                try:
                    # Extract code from link text or nearby elements
                    link_text = link.get_text(strip=True)
                    
                    # Also check parent elements for more context
                    parent = link.parent
                    if parent:
                        context_text = parent.get_text(strip=True)
                        link_text = f"{link_text} {context_text}"
                    
                    # Extract potential codes from the text
                    code_matches = re.findall(r'([A-Z]{2,5})-?(\d{3,4})', link_text.upper())
                    
                    for match in code_matches:
                        found_code = f"{match[0]}{match[1]}"
                        
                        # Calculate match score
                        score = self._calculate_code_match_score(found_code, target_code_clean)
                        
                        if score > best_score:
                            best_score = score
                            best_match = link.get('href')
                            
                except Exception as e:
                    self.logger.debug(f"Error parsing search result link: {e}")
                    continue
            
            if best_match and best_score >= 80:  # Require high confidence match
                self.logger.debug(f"Found best match with score {best_score}: {best_match}")
                return best_match
            
            # If no high-confidence match, return the first result as fallback
            if movie_links:
                fallback_url = movie_links[0].get('href')
                self.logger.debug(f"Using fallback match: {fallback_url}")
                return fallback_url
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing search results: {e}")
            return None
    
    def _calculate_code_match_score(self, found_code: str, target_code: str) -> int:
        """
        Calculate how well a found code matches the target code.
        
        Args:
            found_code: Code found in search results
            target_code: Target code we're looking for
            
        Returns:
            Match score (0-100)
        """
        if found_code == target_code:
            return 100
        
        # Check if one contains the other
        if target_code in found_code or found_code in target_code:
            return 90
        
        # Check for partial matches
        # Extract letter and number parts
        found_match = re.match(r'([A-Z]+)(\d+)', found_code)
        target_match = re.match(r'([A-Z]+)(\d+)', target_code)
        
        if found_match and target_match:
            found_letters, found_numbers = found_match.groups()
            target_letters, target_numbers = target_match.groups()
            
            if found_letters == target_letters:
                # Same letter prefix, check numbers
                if found_numbers == target_numbers:
                    return 95
                elif abs(int(found_numbers) - int(target_numbers)) <= 5:
                    return 70
                else:
                    return 50
        
        return 0
    
    async def _extract_movie_metadata(self, movie_url: str, code: str) -> Optional[MovieMetadata]:
        """
        Extract detailed metadata from movie page.
        
        Args:
            movie_url: URL of the movie page
            code: Movie code
            
        Returns:
            MovieMetadata object or None
        """
        try:
            self.logger.debug(f"Extracting metadata from: {movie_url}")
            
            response = await self.http_client.get(movie_url)
            async with response:
                if response.status != 200:
                    self.logger.error(f"Failed to fetch movie page: {response.status}")
                    return None

                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                metadata = MovieMetadata(
                    code=code,
                    title=self._extract_title(soup) or f"Unknown Title ({code})",
                    actresses=self._extract_actresses(soup),
                    release_date=self._extract_release_date(soup),
                    duration=self._extract_duration(soup),
                    studio=self._extract_studio(soup),
                    series=self._extract_series(soup),
                    genres=self._extract_genres(soup),
                    cover_url=self._extract_cover_image(soup),
                    poster_url=self._extract_cover_image(soup),
                    screenshots=self._extract_screenshots(soup),
                    description=self._extract_description(soup),
                    rating=self._extract_rating(soup),
                    source_url=movie_url
                )

                return metadata
                    
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {movie_url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract movie title."""
        # JavLibrary specific selectors
        selectors = [
            '#video_title .post-title',
            '#video_title h3',
            '.video_title',
            'h3 a[style*="color"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                # Clean up title (remove code if present at start)
                title = re.sub(r'^[A-Z]+-\d+\s*', '', title)
                return title
        
        return None
    
    def _extract_actresses(self, soup: BeautifulSoup) -> List[str]:
        """Extract actress names."""
        actresses = []
        
        # Invalid actress names to filter out
        invalid_names = ['Censored', 'censored', 'CENSORED', 'Uncensored', 'uncensored', 'UNCENSORED', 'Western', 'western', '暂无', '未知', 'Unknown', 'N/A', '-', '---']
        
        # JavLibrary specific selectors for cast
        selectors = [
            '#video_cast .cast a',
            '.cast a[href*="star"]',
            'a[href*="vl_star.php"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                name = elem.get_text(strip=True)
                # Filter out invalid names
                if name and name not in actresses and name not in invalid_names:
                    actresses.append(name)
        
        return actresses
    
    def _extract_release_date(self, soup: BeautifulSoup) -> Optional[date]:
        """Extract release date."""
        # Look for date in video info table
        info_table = soup.find('div', id='video_info')
        if not info_table:
            return None
        
        # Find date patterns in the info section
        date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{4})/(\d{2})/(\d{2})'
        ]
        
        info_text = info_table.get_text()
        
        for pattern in date_patterns:
            matches = re.findall(pattern, info_text)
            for match in matches:
                try:
                    year, month, day = map(int, match)
                    if 1990 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return date(year, month, day)
                except ValueError:
                    continue
        
        return None
    
    def _extract_duration(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract movie duration in minutes."""
        # Look for duration in video info
        info_table = soup.find('div', id='video_info')
        if not info_table:
            return None
        
        # Look for duration patterns
        duration_patterns = [
            r'(\d+)\s*min',
            r'(\d+)\s*分'
        ]
        
        info_text = info_table.get_text()
        
        for pattern in duration_patterns:
            match = re.search(pattern, info_text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_studio(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract studio/maker name."""
        # Look for maker/studio links
        selectors = [
            '#video_maker a',
            'a[href*="vl_maker.php"]',
            '.maker a'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    def _extract_series(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract series name."""
        # Look for series links
        selectors = [
            '#video_series a',
            'a[href*="vl_series.php"]',
            '.series a'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    def _extract_genres(self, soup: BeautifulSoup) -> List[str]:
        """Extract genre tags."""
        genres = []
        
        # Look for genre/category links
        selectors = [
            '#video_genres a',
            'a[href*="vl_genre.php"]',
            '.genre a'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                genre = elem.get_text(strip=True)
                if genre and genre not in genres:
                    genres.append(genre)
        
        return genres
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract movie description."""
        # JavLibrary doesn't typically have detailed descriptions
        # But we can try to find any available text
        selectors = [
            '#video_comments',
            '.description',
            '.synopsis'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                desc = elem.get_text(strip=True)
                if len(desc) > 10:  # Only return if substantial
                    return desc
        
        return None
    
    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract movie rating."""
        # Look for rating information
        rating_selectors = [
            '.rating',
            '#video_review .score',
            '.score'
        ]
        
        for selector in rating_selectors:
            elem = soup.select_one(selector)
            if elem:
                rating_text = elem.get_text(strip=True)
                
                # Try to extract numeric rating
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    try:
                        rating = float(rating_match.group(1))
                        # Normalize to 0-10 scale if needed
                        if rating <= 5:
                            rating = rating * 2
                        return min(10.0, max(0.0, rating))
                    except ValueError:
                        continue
        
        return None
    
    def _extract_cover_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract cover image URL."""
        # Look for the main movie image
        selectors = [
            '#video_jacket_img',
            '#video_jacket img',
            '.jacket img',
            'img[src*="jacket"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                src = elem.get('src')
                if src:
                    # Convert to full URL if needed
                    if not src.startswith('http'):
                        src = urljoin(self.BASE_URL, src)
                    return src
        
        return None
    
    def _extract_screenshots(self, soup: BeautifulSoup) -> List[str]:
        """Extract screenshot URLs."""
        screenshots = []
        
        # Look for preview/sample images
        selectors = [
            '#video_screenshots img',
            '.preview img',
            'img[src*="sample"]',
            'img[src*="screenshot"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                src = elem.get('src')
                if src:
                    # Convert to full URL if needed
                    if not src.startswith('http'):
                        src = urljoin(self.BASE_URL, src)
                    
                    if src not in screenshots:
                        screenshots.append(src)
        
        return screenshots