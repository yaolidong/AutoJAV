"""Tests for HttpClient."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from src.utils.http_client import HttpClient


class TestHttpClient:
    """Test cases for HttpClient."""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Test HttpClient initialization."""
        client = HttpClient(
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            rate_limit_delay=0.5,
            proxy_url="http://proxy.example.com:8080"
        )
        
        assert client.timeout.total == 60
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.rate_limit_delay == 0.5
        assert client.proxy_url == "http://proxy.example.com:8080"
        assert 'User-Agent' in client.default_headers
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test HttpClient as context manager."""
        async with HttpClient() as client:
            assert client._session is not None
            assert not client._session.closed
        
        # Session should be closed after exiting context
        assert client._session.closed
    
    @pytest.mark.asyncio
    async def test_ensure_session(self):
        """Test session creation."""
        client = HttpClient()
        
        # Initially no session
        assert client._session is None
        
        # Create session
        await client._ensure_session()
        assert client._session is not None
        assert not client._session.closed
        
        # Clean up
        await client.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        client = HttpClient(rate_limit_delay=0.1)
        
        # First request should not be delayed
        start_time = asyncio.get_event_loop().time()
        await client._rate_limit()
        first_duration = asyncio.get_event_loop().time() - start_time
        
        # Second request should be delayed
        start_time = asyncio.get_event_loop().time()
        await client._rate_limit()
        second_duration = asyncio.get_event_loop().time() - start_time
        
        assert first_duration < 0.05  # Should be very fast
        assert second_duration >= 0.09  # Should be delayed by ~0.1s
    
    @pytest.mark.asyncio
    async def test_get_request_success(self):
        """Test successful GET request."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            
            mock_session.request.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = HttpClient(rate_limit_delay=0)  # Disable rate limiting for test
            
            response = await client.get("http://example.com")
            
            assert response.status == 200
            mock_session.request.assert_called_once()
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_post_request_with_data(self):
        """Test POST request with data."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 201
            
            mock_session.request.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = HttpClient(rate_limit_delay=0)
            
            response = await client.post(
                "http://example.com/api",
                data={"key": "value"},
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status == 201
            
            # Check that request was called with correct parameters
            call_args = mock_session.request.call_args
            assert call_args[0][0] == 'POST'  # method
            assert call_args[0][1] == "http://example.com/api"  # url
            assert 'data' in call_args[1]
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism on request failure."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            # First two calls fail, third succeeds
            mock_session.request.side_effect = [
                aiohttp.ClientError("Connection failed"),
                aiohttp.ClientError("Connection failed"),
                AsyncMock(status=200, reason="OK")
            ]
            mock_session_class.return_value = mock_session
            
            client = HttpClient(max_retries=2, retry_delay=0.01, rate_limit_delay=0)
            
            response = await client.get("http://example.com")
            
            assert response.status == 200
            assert mock_session.request.call_count == 3  # 1 initial + 2 retries
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.request.side_effect = aiohttp.ClientError("Connection failed")
            mock_session_class.return_value = mock_session
            
            client = HttpClient(max_retries=1, retry_delay=0.01, rate_limit_delay=0)
            
            with pytest.raises(aiohttp.ClientError):
                await client.get("http://example.com")
            
            assert mock_session.request.call_count == 2  # 1 initial + 1 retry
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_rate_limit_response(self):
        """Test handling of 429 rate limit response."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            
            # First response is rate limited, second succeeds
            rate_limited_response = AsyncMock()
            rate_limited_response.status = 429
            rate_limited_response.headers = {'Retry-After': '0.1'}
            
            success_response = AsyncMock()
            success_response.status = 200
            
            mock_session.request.side_effect = [rate_limited_response, success_response]
            mock_session_class.return_value = mock_session
            
            client = HttpClient(rate_limit_delay=0)
            
            response = await client.get("http://example.com")
            
            assert response.status == 200
            assert mock_session.request.call_count == 2
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_download_file_success(self):
        """Test successful file download."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.iter_chunked.return_value = [b'chunk1', b'chunk2']
            
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = HttpClient(rate_limit_delay=0)
            
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                success = await client.download_file("http://example.com/file.jpg", "/tmp/file.jpg")
                
                assert success is True
                assert mock_file.write.call_count == 2  # Two chunks
                mock_file.write.assert_any_call(b'chunk1')
                mock_file.write.assert_any_call(b'chunk2')
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_download_file_failure(self):
        """Test file download failure."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 404
            
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = HttpClient(rate_limit_delay=0)
            
            success = await client.download_file("http://example.com/notfound.jpg", "/tmp/file.jpg")
            
            assert success is False
            
            await client.close()
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        client = HttpClient(
            max_retries=5,
            rate_limit_delay=1.5,
            proxy_url="http://proxy.example.com:8080"
        )
        
        stats = client.get_stats()
        
        assert stats['request_count'] == 0
        assert stats['session_active'] is False
        assert stats['proxy_url'] == "http://proxy.example.com:8080"
        assert stats['max_retries'] == 5
        assert stats['rate_limit_delay'] == 1.5
    
    @pytest.mark.asyncio
    async def test_custom_headers(self):
        """Test custom headers in requests."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            
            mock_session.request.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            client = HttpClient(
                rate_limit_delay=0,
                user_agent="Custom User Agent"
            )
            
            custom_headers = {"Authorization": "Bearer token123"}
            await client.get("http://example.com", headers=custom_headers)
            
            # Check that headers were merged correctly
            call_args = mock_session.request.call_args
            headers = call_args[1]['headers']
            
            assert headers['User-Agent'] == "Custom User Agent"
            assert headers['Authorization'] == "Bearer token123"
            
            await client.close()