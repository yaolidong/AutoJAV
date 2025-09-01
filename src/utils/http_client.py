"""HTTP client for making web requests with retry and rate limiting."""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Union
from urllib.parse import urljoin, urlparse
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError


class HttpClient:
    """Async HTTP client with retry logic and rate limiting."""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit_delay: float = 1.0,
        proxy_url: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Initialize the HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            rate_limit_delay: Minimum delay between requests in seconds
            proxy_url: Proxy URL for requests
            user_agent: Custom User-Agent header
        """
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.proxy_url = proxy_url
        self.logger = logging.getLogger(__name__)
        
        # Default headers
        self.default_headers = {
            'User-Agent': user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self._session: Optional[ClientSession] = None
        self._last_request_time = 0.0
        self._request_count = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure the HTTP session is created."""
        if self._session is None or self._session.closed:
            connector_kwargs = {}
            if self.proxy_url:
                connector_kwargs['trust_env'] = True
            
            connector = aiohttp.TCPConnector(**connector_kwargs)
            
            self._session = ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers=self.default_headers
            )
            self.logger.debug("Created new HTTP session")
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("Closed HTTP session")
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make a GET request.
        
        Args:
            url: URL to request
            headers: Additional headers
            params: Query parameters
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            HTTP response object
            
        Raises:
            aiohttp.ClientError: If request fails after all retries
        """
        return await self._request('GET', url, headers=headers, params=params, **kwargs)
    
    async def post(
        self,
        url: str,
        data: Optional[Union[Dict, str, bytes]] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make a POST request.
        
        Args:
            url: URL to request
            data: Form data or raw data
            json: JSON data
            headers: Additional headers
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            HTTP response object
            
        Raises:
            aiohttp.ClientError: If request fails after all retries
        """
        return await self._request('POST', url, data=data, json=json, headers=headers, **kwargs)
    
    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: URL to request
            headers: Additional headers
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            HTTP response object
            
        Raises:
            aiohttp.ClientError: If request fails after all retries
        """
        await self._ensure_session()
        await self._rate_limit()
        
        # Merge headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Add proxy if configured
        if self.proxy_url:
            kwargs['proxy'] = self.proxy_url
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self._request_count += 1
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self._session.request(
                    method,
                    url,
                    headers=request_headers,
                    **kwargs
                )
                
                # Log response info
                self.logger.debug(f"Response: {response.status} {response.reason}")
                
                # Check for rate limiting
                if response.status == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait_time = float(retry_after)
                            self.logger.warning(f"Rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        except ValueError:
                            pass
                
                # Return response for any status code (let caller handle errors)
                return response
                
            except (ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.debug(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Request failed after {self.max_retries + 1} attempts")
        
        # If we get here, all retries failed
        raise last_exception or ClientError("Request failed")
    
    async def download_file(
        self,
        url: str,
        file_path: str,
        headers: Optional[Dict[str, str]] = None,
        chunk_size: int = 8192
    ) -> bool:
        """
        Download a file from URL.
        
        Args:
            url: URL to download from
            file_path: Local path to save file
            headers: Additional headers
            chunk_size: Size of chunks to read
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            async with await self.get(url, headers=headers) as response:
                if response.status == 200:
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                    
                    self.logger.debug(f"Downloaded file: {url} -> {file_path}")
                    return True
                else:
                    self.logger.error(f"Download failed: {response.status} {response.reason}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error downloading file {url}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Dictionary with client statistics
        """
        return {
            'request_count': self._request_count,
            'session_active': self._session is not None and not self._session.closed,
            'proxy_url': self.proxy_url,
            'max_retries': self.max_retries,
            'rate_limit_delay': self.rate_limit_delay
        }