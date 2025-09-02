"""
JAVBus scraper for fetching movie metadata without login
"""

import re
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup
import aiohttp

from .base_scraper import BaseScraper
from ..models.movie_metadata import MovieMetadata
from ..utils.http_client import HttpClient


import asyncio

class JAVBusScraper(BaseScraper):
    """Scraper for JAVBus website (no login required)."""
    
    BASE_URL = "https://www.javbus.com"
    SEARCH_URL = f"{BASE_URL}/search"
    
    def __init__(self, http_client: Optional[HttpClient] = None):
        """
        Initialize JAVBus scraper.
        
        Args:
            http_client: HTTP client instance for making requests
        """
        super().__init__("JAVBus")
        self.http_client = http_client or HttpClient(
            timeout=30,
            rate_limit_delay=1.0,
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        )
        self.logger = logging.getLogger(__name__)
        
        # Cache for availability check
        self._is_available = None
        self._last_availability_check = None
    
    async def check_availability(self) -> bool:
        """Check if JAVBus is accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={'User-Agent': self.http_client.default_headers.get('User-Agent')}
                ) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"JAVBus availability check failed: {e}")
            return False
    
    async def scrape_async(self, code: str) -> Optional[MovieMetadata]:
        """
        Scrape metadata for a movie code asynchronously.
        
        Args:
            code: Movie code to search for
            
        Returns:
            MovieMetadata if found, None otherwise
        """
        if not code:
            return None
        
        self.logger.info(f"Scraping JAVBus for code: {code}")
        
        try:
            # Search for the movie
            search_url = f"{self.BASE_URL}/{code}"
            
            # Create session with cookies for age verification
            cookies = {
                'existmag': 'mag',  # Age verification cookie
                'age': 'verified'   # Additional age cookie
            }
            
            async with aiohttp.ClientSession(cookies=cookies) as session:
                async with session.get(
                    search_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={'User-Agent': self.http_client.default_headers.get('User-Agent')}
                ) as response:
                    
                    if response.status != 200:
                        self.logger.debug(f"JAVBus returned status {response.status} for {code}")
                        return None
                    
                    html = await response.text()
                    return await self._parse_movie_page(html, code, search_url)
                    
        except asyncio.TimeoutError:
            self.logger.warning(f"JAVBus timeout for {code}")
            return None
        except Exception as e:
            self.logger.error(f"Error scraping JAVBus for {code}: {e}")
            return None
    
    def scrape(self, code: str) -> Optional[MovieMetadata]:
        """
        Synchronous wrapper for scraping.
        
        Args:
            code: Movie code to search for
            
        Returns:
            MovieMetadata if found, None otherwise
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.scrape_async(code))
    
    async def _parse_movie_page(self, html: str, code: str, url: str) -> Optional[MovieMetadata]:
        """
        Parse movie page HTML to extract metadata.
        
        Args:
            html: HTML content of the movie page
            code: Movie code
            url: URL of the movie page
            
        Returns:
            MovieMetadata if successfully parsed, None otherwise
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Check if it's a valid movie page
            container = soup.find('div', class_='container')
            if not container:
                return None
            
            # Extract title
            title_elem = soup.find('h3')
            title = title_elem.text.strip() if title_elem else code
            
            # Extract cover image
            cover_url = None
            cover_elem = soup.find('a', class_='bigImage')
            if cover_elem and cover_elem.get('href'):
                cover_url = cover_elem['href']
            elif soup.find('img', class_='video-cover'):
                cover_url = soup.find('img', class_='video-cover').get('src')
            
            # Extract info from info panel
            info_panel = soup.find('div', class_='col-md-3')
            if not info_panel:
                return None
            
            # Parse info items
            info_dict = {}
            for p in info_panel.find_all('p'):
                text = p.text.strip()
                if '：' in text:
                    key, value = text.split('：', 1)
                    info_dict[key.strip()] = value.strip()
                elif ':' in text:
                    key, value = text.split(':', 1)
                    info_dict[key.strip()] = value.strip()
            
            # Extract metadata from info dict
            release_date = self._parse_date(info_dict.get('發行日期', info_dict.get('发行日期', '')))
            duration_str = info_dict.get('長度', info_dict.get('长度', ''))
            duration = self._parse_duration(duration_str)
            director = info_dict.get('導演', info_dict.get('导演'))
            studio = info_dict.get('製作商', info_dict.get('制作商'))
            series = info_dict.get('系列', info_dict.get('系列'))
            
            # Extract actresses
            actresses = []
            # Invalid actress names to filter out
            invalid_names = ['Censored', 'censored', 'CENSORED', 'Uncensored', 'uncensored', 'UNCENSORED', 'Western', 'western', '暂无', '未知', 'Unknown', 'N/A', '-', '---']
            
            actress_container = soup.find('div', class_='star-name')
            if actress_container:
                for link in actress_container.find_all('a'):
                    actress_name = link.text.strip()
                    # Filter out invalid names
                    if actress_name and actress_name not in invalid_names:
                        actresses.append(actress_name)
            
            # If no actresses found, try alternative location
            if not actresses:
                for p in info_panel.find_all('p'):
                    if '演員' in p.text or '女优' in p.text:
                        for link in p.find_all('a'):
                            actress_name = link.text.strip()
                            # Filter out invalid names
                            if actress_name and actress_name not in invalid_names:
                                actresses.append(actress_name)
            
            # Extract genres
            genres = []
            genre_container = soup.find('div', class_='genre')
            if genre_container:
                for link in genre_container.find_all('a'):
                    genre = link.text.strip()
                    if genre:
                        genres.append(genre)
            
            # Extract sample images
            gallery_urls = []
            sample_container = soup.find('div', id='sample-waterfall')
            if sample_container:
                for link in sample_container.find_all('a', class_='sample-box'):
                    img_url = link.get('href')
                    if img_url:
                        gallery_urls.append(img_url)
            
            # Create metadata object
            metadata = MovieMetadata(
                code=code.upper(),
                title=title,
                actresses=actresses if actresses else ["未知女优"],
                release_date=release_date,
                studio=studio,
                director=director,
                duration=duration,
                series=series,
                genres=genres,
                cover_url=cover_url,
                gallery_urls=gallery_urls,
                source_urls={'JAVBus': url}
            )
            
            self.logger.info(f"Successfully scraped metadata from JAVBus for {code}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error parsing JAVBus page for {code}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            # Try to extract date with regex
            match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', date_str)
            if match:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
                
        except Exception as e:
            self.logger.debug(f"Could not parse date '{date_str}': {e}")
        
        return None
    
    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string to minutes."""
        if not duration_str:
            return None
        
        try:
            # Extract number from string
            match = re.search(r'(\d+)', duration_str)
            if match:
                return int(match.group(1))
        except Exception as e:
            self.logger.debug(f"Could not parse duration '{duration_str}': {e}")
        
        return None
    
    def is_available(self) -> bool:
        """Check if the scraper is available (synchronous wrapper)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.check_availability())
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """Search for a movie by code."""
        return await self.scrape_async(code)