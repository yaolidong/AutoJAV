"""JavDB scraper for fetching movie metadata."""

import re
import logging
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, quote, urlparse
from datetime import datetime, date
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from .base_scraper import BaseScraper
from ..models.movie_metadata import MovieMetadata
from ..utils.webdriver_manager import WebDriverManager
from ..utils.login_manager import LoginManager
from ..utils.javdb_login import JavDBCookieManager


class JavDBScraper(BaseScraper):
    """Scraper for JavDB website."""

    DEFAULT_BASE_URL = "https://javdb563.com"
    
    def __init__(
        self,
        driver_manager: WebDriverManager,
        login_manager: Optional[LoginManager] = None,
        use_login: bool = True,
        config_dir: str = "/app/config",
        base_url: Optional[str] = None
    ):
        """
        Initialize JavDB scraper.
        
        Args:
            driver_manager: WebDriver manager instance
            login_manager: Login manager for authentication
            use_login: Whether to use login for better access
            config_dir: Directory for config and cookie files
        """
        super().__init__("JavDB")
        self.driver_manager = driver_manager
        self.login_manager = login_manager
        self.use_login = use_login
        self.logger = logging.getLogger(__name__)
        
        normalized_base_url = base_url or self.DEFAULT_BASE_URL
        parsed = urlparse(normalized_base_url)
        if not parsed.scheme:
            normalized_base_url = f"https://{normalized_base_url.lstrip('/')}"
            parsed = urlparse(normalized_base_url)
        self.base_url = normalized_base_url.rstrip('/')
        self.base_domain = parsed.hostname or "javdb.com"
        self.search_url = f"{self.base_url}/search"
        self.login_url = f"{self.base_url}/login"
        
        # Manual cookie manager: user pastes cookies via CLI utility
        self.cookie_manager = JavDBCookieManager(config_dir=Path(config_dir))
        
        # Cache for availability check
        self._availability_cache = None
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes
        
        # Rate limiting
        self._last_request_time = 0
        self._request_delay = 2.0  # 2 seconds between requests
        
        # Track if cookies have been applied
        self._cookies_applied = False
    
    async def is_available(self) -> bool:
        """
        Check if JavDB is available and accessible.
        This check is now more lenient, mainly ensuring a basic connection.
        The main search function has more robust handling for CAPTCHA etc.
        """
        # Check cache first
        if self._is_cache_valid():
            return self._availability_cache

        try:
            self.logger.debug("Checking JavDB availability...")
            # A simple check: can we get the homepage?
            success = self.driver_manager.get_page(self.base_url, wait_for_element="head")
            if not success:
                self.logger.warning(f"Failed to load JavDB base URL: {self.base_url}")
                self._availability_cache = False
                self._cache_timestamp = datetime.now()
                return False

            # Check for a title to make sure it's not a blank page
            await asyncio.sleep(1) # Give title time to render
            page_title = self.driver_manager.driver.title
            self.logger.debug(f"JavDB page title: {page_title}")

            # If title suggests it's a normal page, we consider it available.
            # Cloudflare pages often have specific titles like "Just a moment..."
            if page_title and 'javdb' in page_title.lower():
                self.logger.info("JavDB is considered available.")
                self._availability_cache = True
            else:
                # It might be a Cloudflare page, but we'll let the search function handle it.
                self.logger.warning(f"JavDB availability check inconclusive (Title: {page_title}). Proceeding anyway.")
                self._availability_cache = True # Assume available and let search handle it

            self._cache_timestamp = datetime.now()
            return self._availability_cache

        except Exception as e:
            self.logger.error(f"Error checking JavDB availability: {e}")
            self._availability_cache = False
            self._cache_timestamp = datetime.now()
            return False
    
    def _is_cache_valid(self) -> bool:
        """Check if availability cache is still valid."""
        if self._availability_cache is None or self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_duration

    async def cleanup(self):
        """Clean up resources used by the scraper, like the WebDriver."""
        self.logger.info("Cleaning up JavDBScraper resources...")
        if self.driver_manager:
            self.driver_manager.quit_driver()
    
    async def _ensure_logged_in(self) -> bool:
        """
        Simplified login process to mimic the successful debug script.
        Focuses on just landing on the page and waiting.
        """
        try:
            self.logger.info("Ensuring browser is on the correct domain and stable.")
            driver = self.driver_manager.driver
            if not driver:
                self.logger.info("Starting WebDriver...")
                driver = self.driver_manager.start_driver()

            # Just navigate and wait, like the debug script.
            self.logger.info(f"Navigating to {self.base_url} to establish a stable session.")
            self.driver_manager.get_page(self.base_url)

            # Apply manually provided cookies once
            if not self._cookies_applied:
                try:
                    cookies = self.cookie_manager.load_cookies()
                    for name, value in cookies.items():
                        try:
                            driver.add_cookie({
                                "name": name,
                                "value": value,
                                "domain": self.base_domain,
                                "path": "/",
                            })
                        except Exception as cookie_exc:  # noqa: BLE001
                            self.logger.debug("Failed to add cookie %s: %s", name, cookie_exc)
                    self._cookies_applied = True
                    self.logger.info("Applied %d manual JavDB cookies", len(cookies))
                    driver.get(self.base_url)
                except FileNotFoundError:
                    self.logger.warning("未找到手动输入的 JavDB Cookie 文件，访问可能受限")
                except Exception as exc:  # noqa: BLE001
                    self.logger.warning("应用 JavDB Cookie 失败: %s", exc)

            self.logger.info("Waiting 15 seconds for any Cloudflare checks to complete...")
            await asyncio.sleep(15)

            page_title = driver.title
            self.logger.info(f"Landed on page with title: {page_title}")
            
            # Assume success if we didn't crash and got a title.
            return True

        except Exception as e:
            self.logger.error(f"An error occurred during the simplified login process: {e}")
            return False
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        import time
        
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._request_delay:
            sleep_time = self._request_delay - elapsed
            self.logger.debug(f"Rate limiting: waiting {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """
        Search for movie metadata by code.
        
        Args:
            code: Movie code to search for
            
        Returns:
            MovieMetadata if found, None otherwise
        """
        try:
            # Try to ensure logged in first (this will apply cookies if available)
            await self._ensure_logged_in()
            
            # Then check availability - but log warning instead of failing
            is_available = await self.is_available()
            if not is_available:
                self.logger.warning("JavDB may not be fully available, attempting with cookies anyway")
                # Continue trying even if availability check fails
            
            # Apply rate limiting
            await self._rate_limit()
            
            self.logger.info(f"Searching JavDB for code: {code}")
            
            # Search for the movie
            search_results = await self._search_by_code(code)
            
            if not search_results:
                self.logger.info(f"No results found for code: {code}")
                return None
            
            # Get the best match
            best_match = self._find_best_match(search_results, code)
            
            if not best_match:
                self.logger.info(f"No suitable match found for code: {code}")
                return None
            
            # Extract detailed metadata
            metadata = await self._extract_movie_metadata(best_match['url'], code)
            
            if metadata:
                self.logger.info(f"Successfully scraped metadata for: {code}")
            else:
                self.logger.warning(f"Failed to extract metadata for: {code}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error searching for {code}: {e}")
            return None
    
    async def _search_by_code(self, code: str) -> List[Dict[str, Any]]:
        """
        Search JavDB by movie code.
        
        Args:
            code: Movie code to search for
            
        Returns:
            List of search results
        """
        try:
            # Construct search URL
            search_query = quote(code)
            search_url = f"{self.search_url}?q={search_query}&f=all"
            
            self.logger.debug(f"Searching URL: {search_url}")
            
            # Navigate to search page
            if not self.driver_manager.get_page(search_url):
                self.logger.warning(f"Failed to navigate to search URL: {search_url}")
                return []
            
            # Wait for results to load - increase wait time to ensure full load
            await asyncio.sleep(5)
            
            # Take a screenshot for debugging
            screenshot_path = f"/tmp/javdb_search_{code.replace('/', '_')}.png"
            if self.driver_manager.take_screenshot(screenshot_path):
                self.logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Additional wait for dynamic content
            try:
                self.driver_manager.wait_for_element('div.item', timeout=10)
            except Exception:
                self.logger.debug("No search results found or timeout waiting for items")
            
            # Parse search results
            page_source = self.driver_manager.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            results = []
            
            # Find movie items in search results
            movie_items = soup.find_all('div', class_='item')
            
            self.logger.info(f"Found {len(movie_items)} movie items on search page")
            
            # If no items found, check if we're on the right page
            if not movie_items:
                # Check for alternative item containers
                movie_items = soup.find_all('div', class_='movie-list') or soup.find_all('div', class_='grid-item')
                if movie_items:
                    self.logger.info(f"Found {len(movie_items)} items using alternative selector")
                else:
                    # Log page title to understand where we are
                    page_title = soup.find('title')
                    if page_title:
                        self.logger.warning(f"No items found. Page title: {page_title.text}")
                    
                    # Check if we're blocked or need to log in
                    if 'cloudflare' in page_source.lower() or 'cf-browser-verification' in page_source.lower():
                        self.logger.error("Cloudflare protection detected on search page")
                    elif 'login' in page_source.lower() and 'password' in page_source.lower():
                        self.logger.warning("Login page detected - cookies may not be working")
            
            for item in movie_items:
                try:
                    result = self._parse_search_result_item(item)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.debug(f"Error parsing search result item: {e}")
                    continue
            
            self.logger.debug(f"Found {len(results)} search results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching by code {code}: {e}")
            return []
    
    def _parse_search_result_item(self, item) -> Optional[Dict[str, Any]]:
        """
        Parse a single search result item.
        
        Args:
            item: BeautifulSoup element for the item
            
        Returns:
            Dictionary with item data or None
        """
        try:
            # Find the link to the movie page
            link_elem = item.find('a')
            if not link_elem or not link_elem.get('href'):
                return None
            
            url = urljoin(self.base_url, link_elem['href'])
            
            # Extract title
            title_elem = item.find('div', class_='video-title') or item.find('strong')
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract code from title or URL
            code_match = re.search(r'([A-Z]{2,5})-?(\d{3,4})', title.upper())
            detected_code = f"{code_match.group(1)}-{code_match.group(2)}" if code_match else ""
            
            # Extract thumbnail
            img_elem = item.find('img')
            thumbnail = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
            if thumbnail and not thumbnail.startswith('http'):
                thumbnail = urljoin(self.base_url, thumbnail)
            
            # Extract additional info
            meta_elem = item.find('div', class_='meta')
            meta_text = meta_elem.get_text(strip=True) if meta_elem else ""
            
            return {
                'url': url,
                'title': title,
                'code': detected_code,
                'thumbnail': thumbnail,
                'meta': meta_text
            }
            
        except Exception as e:
            self.logger.debug(f"Error parsing search result item: {e}")
            return None
    
    def _find_best_match(self, results: List[Dict[str, Any]], target_code: str) -> Optional[Dict[str, Any]]:
        """
        Find the best matching result for the target code.
        
        Args:
            results: List of search results
            target_code: Target movie code
            
        Returns:
            Best matching result or None
        """
        if not results:
            return None
        
        target_code_clean = re.sub(r'[^A-Z0-9]', '', target_code.upper())
        
        # Score each result
        scored_results = []
        
        for result in results:
            score = 0
            result_code = result.get('code', '').upper()
            result_code_clean = re.sub(r'[^A-Z0-9]', '', result_code)
            
            # Exact match gets highest score
            if result_code_clean == target_code_clean:
                score = 100
            # Partial match
            elif target_code_clean in result_code_clean or result_code_clean in target_code_clean:
                score = 80
            # Title contains the code
            elif target_code_clean in result.get('title', '').upper():
                score = 60
            
            if score > 0:
                scored_results.append((score, result))
        
        if not scored_results:
            # If no good matches, return the first result
            return results[0]
        
        # Return the highest scored result
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results[0][1]
    
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
            
            # Navigate to movie page
            if not self.driver_manager.get_page(movie_url):
                return None
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Parse the page
            page_source = self.driver_manager.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract basic information
            title = self._extract_title(soup)
            title_en = self._extract_english_title(soup)
            actresses = self._extract_actresses(soup)
            release_date = self._extract_release_date(soup)
            duration = self._extract_duration(soup)
            studio = self._extract_studio(soup)
            series = self._extract_series(soup)
            genres = self._extract_genres(soup)
            description = self._extract_description(soup)
            rating = self._extract_rating(soup)
            
            # Extract images
            cover_url = self._extract_cover_image(soup)
            poster_url = self._extract_poster_image(soup)
            screenshots = self._extract_screenshots(soup)
            
            # Create metadata object
            metadata = MovieMetadata(
                code=code,
                title=title or f"Unknown Title ({code})",
                title_en=title_en,
                actresses=actresses,
                release_date=release_date,
                duration=duration,
                studio=studio,
                series=series,
                genres=genres,
                cover_url=cover_url,
                poster_url=poster_url,
                screenshots=screenshots,
                description=description,
                rating=rating,
                source_urls={'JavDB': movie_url}
            )

            metadata.add_source('JavDB', movie_url)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {movie_url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract movie title."""
        selectors = [
            'h2.title',
            '.movie-title',
            'h1',
            '.video-title strong'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    def _extract_english_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract English title if available."""
        # Look for English title in various places
        selectors = [
            '.title-en',
            '.english-title',
            '[lang="en"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    def _extract_actresses(self, soup: BeautifulSoup) -> List[str]:
        """Extract actress names."""
        actresses = []
        
        # Invalid actress names to filter out
        invalid_names = ['Censored', 'censored', 'CENSORED', 'Uncensored', 'uncensored', 'UNCENSORED', 
                        'Western', 'western', '暂无', '未知', 'Unknown', 'N/A', '-', '---', 
                        '有碼', '有码', '無碼', '无码', '素人', '有碼', '無碼',
                        '歐美', '欧美', '日本', '韩国', '韓國', '中国', '中國',
                        'FC2', '動漫', '动漫', '卡通', '3D', '2D',
                        '鯨魚', '鲸鱼', '鮑魚', '鲍鱼', '鯖島', '鯖島', '鯵島',
                        '久道実', 'ゆうき', '100%']
        
        # Look for actress links or names - prioritize actor links
        selectors = [
            'a[href*="/actors/"]',  # Primary selector for JavDB
            '.panel-body a[href*="/actors/"]',  # More specific
            '.actress-name',
            '.performer a',
            '.star a'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    name = elem.get_text(strip=True)
                    # Filter out invalid names and check minimum length
                    if name and len(name) > 1 and name not in actresses and name not in invalid_names:
                        # Additional check: skip if it looks like a category or genre
                        category_keywords = ['碼', '码', '類', '类', '片', '系列', 'FC2', '動漫', '歐美']
                        if not any(keyword in name for keyword in category_keywords):
                            # Skip if name contains only numbers or special characters
                            if not name.isdigit() and not all(c in '.-_/' for c in name):
                                self.logger.debug(f"Found actress: {name}")
                                actresses.append(name)
            except Exception as e:
                self.logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        # Log result for debugging
        if actresses:
            self.logger.info(f"Extracted actresses for movie: {actresses}")
        else:
            self.logger.warning(f"No actresses found for movie")
        
        return actresses
    
    def _extract_release_date(self, soup: BeautifulSoup) -> Optional[date]:
        """Extract release date."""
        # Look for date in various formats
        date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{4})/(\d{2})/(\d{2})',
            r'(\d{4})\.(\d{2})\.(\d{2})'
        ]
        
        # Search in page text
        page_text = soup.get_text()
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                try:
                    year, month, day = map(int, match)
                    if 2000 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return date(year, month, day)
                except ValueError:
                    continue
        
        return None
    
    def _extract_duration(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract movie duration in minutes."""
        # Look for duration patterns
        duration_patterns = [
            r'(\d+)\s*分',  # Japanese minutes
            r'(\d+)\s*min',
            r'(\d+)\s*minutes?'
        ]
        
        page_text = soup.get_text()
        
        for pattern in duration_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_studio(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract studio/maker name."""
        selectors = [
            'a[href*="/makers/"]',
            '.studio-name',
            '.maker a',
            '.publisher'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    def _extract_series(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract series name."""
        selectors = [
            'a[href*="/series/"]',
            '.series-name',
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
        
        selectors = [
            'a[href*="/tags/"]',
            'a[href*="/genres/"]',
            '.genre a',
            '.tag a'
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
        selectors = [
            '.description',
            '.synopsis',
            '.plot',
            '.summary'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return None
    
    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract movie rating."""
        # Look for rating patterns
        rating_patterns = [
            r'(\d+\.?\d*)\s*/\s*10',
            r'(\d+\.?\d*)\s*/\s*5',
            r'Rating:\s*(\d+\.?\d*)'
        ]
        
        page_text = soup.get_text()
        
        for pattern in rating_patterns:
            match = re.search(pattern, page_text)
            if match:
                try:
                    rating = float(match.group(1))
                    # Normalize to 0-10 scale
                    if '/5' in pattern:
                        rating = rating * 2
                    return min(10.0, max(0.0, rating))
                except ValueError:
                    continue
        
        return None
    
    def _extract_cover_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract cover image URL."""
        selectors = [
            '.movie-poster img',
            '.cover img',
            '.thumbnail img',
            'img[src*="cover"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                src = elem.get('src') or elem.get('data-src')
                if src:
                    return urljoin(self.base_url, src) if not src.startswith('http') else src
        
        return None
    
    def _extract_poster_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract poster image URL."""
        # Often the same as cover for JavDB
        return self._extract_cover_image(soup)
    
    def _extract_screenshots(self, soup: BeautifulSoup) -> List[str]:
        """Extract screenshot URLs."""
        screenshots = []
        
        selectors = [
            '.preview-images img',
            '.screenshots img',
            '.sample-images img',
            'img[src*="sample"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                src = elem.get('src') or elem.get('data-src')
                if src:
                    full_url = urljoin(self.base_url, src) if not src.startswith('http') else src
                    if full_url not in screenshots:
                        screenshots.append(full_url)
        
        return screenshots