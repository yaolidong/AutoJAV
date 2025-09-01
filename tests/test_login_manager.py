"""Tests for LoginManager."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.utils.login_manager import LoginManager
from src.utils.webdriver_manager import WebDriverManager


class TestLoginManager:
    """Test cases for LoginManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_driver_manager = MagicMock(spec=WebDriverManager)
        self.mock_driver = MagicMock()
        self.mock_driver_manager.driver = self.mock_driver
        self.mock_driver_manager.get_page.return_value = True
        
        # Create temporary cookies file
        self.temp_cookies = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_cookies.close()
        
        self.login_manager = LoginManager(
            username="testuser",
            password="testpass",
            driver_manager=self.mock_driver_manager,
            cookies_file=self.temp_cookies.name
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_cookies.name).unlink(missing_ok=True)
    
    def test_init(self):
        """Test LoginManager initialization."""
        assert self.login_manager.username == "testuser"
        assert self.login_manager.password == "testpass"
        assert self.login_manager.driver_manager == self.mock_driver_manager
        assert self.login_manager.cookies_file == self.temp_cookies.name
        assert self.login_manager._is_logged_in is False
        assert self.login_manager._login_attempts == 0
    
    def test_can_attempt_login_allowed(self):
        """Test login attempt when allowed."""
        assert self.login_manager._can_attempt_login() is True
    
    def test_can_attempt_login_max_attempts_exceeded(self):
        """Test login attempt when max attempts exceeded."""
        self.login_manager._login_attempts = 5  # Exceed max
        assert self.login_manager._can_attempt_login() is False
    
    def test_can_attempt_login_cooldown_active(self):
        """Test login attempt during cooldown period."""
        self.login_manager._last_login_attempt = datetime.now()
        assert self.login_manager._can_attempt_login() is False
    
    def test_can_attempt_login_cooldown_expired(self):
        """Test login attempt after cooldown expired."""
        self.login_manager._last_login_attempt = datetime.now() - timedelta(seconds=120)
        assert self.login_manager._can_attempt_login() is True
    
    @pytest.mark.asyncio
    async def test_save_cookies_success(self):
        """Test successful cookie saving."""
        # Mock cookies from driver
        mock_cookies = [
            {'name': 'session', 'value': 'abc123', 'domain': 'example.com'},
            {'name': 'user', 'value': 'testuser', 'domain': 'example.com', 'expiry': 9999999999}
        ]
        self.mock_driver.get_cookies.return_value = mock_cookies
        
        success = await self.login_manager.save_cookies()
        
        assert success is True
        assert len(self.login_manager._session_cookies) == 2
        
        # Check file was created
        cookies_path = Path(self.temp_cookies.name)
        assert cookies_path.exists()
        
        # Check file content
        with open(cookies_path, 'r') as f:
            saved_cookies = json.load(f)
        assert len(saved_cookies) == 2
    
    @pytest.mark.asyncio
    async def test_save_cookies_filter_expired(self):
        """Test cookie saving filters out expired cookies."""
        import time
        
        # Mock cookies with one expired
        mock_cookies = [
            {'name': 'valid', 'value': 'abc123', 'domain': 'example.com'},
            {'name': 'expired', 'value': 'old123', 'domain': 'example.com', 'expiry': time.time() - 3600}
        ]
        self.mock_driver.get_cookies.return_value = mock_cookies
        
        success = await self.login_manager.save_cookies()
        
        assert success is True
        assert len(self.login_manager._session_cookies) == 1
        assert self.login_manager._session_cookies[0]['name'] == 'valid'
    
    @pytest.mark.asyncio
    async def test_load_cookies_success(self):
        """Test successful cookie loading."""
        # Create cookies file
        cookies_data = [
            {'name': 'session', 'value': 'abc123', 'domain': 'example.com'},
            {'name': 'user', 'value': 'testuser', 'domain': 'example.com'}
        ]
        
        with open(self.temp_cookies.name, 'w') as f:
            json.dump(cookies_data, f)
        
        success = await self.login_manager.load_cookies()
        
        assert success is True
        assert len(self.login_manager._session_cookies) == 2
    
    @pytest.mark.asyncio
    async def test_load_cookies_file_not_found(self):
        """Test cookie loading when file doesn't exist."""
        # Remove the temp file
        Path(self.temp_cookies.name).unlink()
        
        success = await self.login_manager.load_cookies()
        
        assert success is False
        assert len(self.login_manager._session_cookies) == 0
    
    @pytest.mark.asyncio
    async def test_load_cookies_invalid_json(self):
        """Test cookie loading with invalid JSON."""
        # Write invalid JSON
        with open(self.temp_cookies.name, 'w') as f:
            f.write("invalid json content")
        
        success = await self.login_manager.load_cookies()
        
        assert success is False
    
    def test_clear_cookies(self):
        """Test cookie clearing."""
        # Create cookies file
        with open(self.temp_cookies.name, 'w') as f:
            json.dump([{'name': 'test'}], f)
        
        self.login_manager._session_cookies = [{'name': 'test'}]
        
        self.login_manager.clear_cookies()
        
        assert len(self.login_manager._session_cookies) == 0
        assert not Path(self.temp_cookies.name).exists()
    
    @pytest.mark.asyncio
    async def test_fill_login_form_success(self):
        """Test successful login form filling."""
        # Mock successful form filling
        self.mock_driver_manager.send_keys.return_value = True
        
        success = await self.login_manager._fill_login_form()
        
        assert success is True
        assert self.mock_driver_manager.send_keys.call_count >= 2  # Username and password
    
    @pytest.mark.asyncio
    async def test_fill_login_form_username_not_found(self):
        """Test login form filling when username field not found."""
        # Mock username field not found, password field found
        def mock_send_keys(selector, text):
            if text == "testuser":
                return False  # Username field not found
            return True  # Password field found
        
        self.mock_driver_manager.send_keys.side_effect = mock_send_keys
        
        success = await self.login_manager._fill_login_form()
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_fill_login_form_password_not_found(self):
        """Test login form filling when password field not found."""
        # Mock username field found, password field not found
        def mock_send_keys(selector, text):
            if text == "testuser":
                return True  # Username field found
            return False  # Password field not found
        
        self.mock_driver_manager.send_keys.side_effect = mock_send_keys
        
        success = await self.login_manager._fill_login_form()
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_handle_captcha_not_present(self):
        """Test captcha handling when no captcha present."""
        self.mock_driver_manager.find_element.return_value = None
        
        success = await self.login_manager._handle_captcha()
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_handle_captcha_present(self):
        """Test captcha handling when captcha is present."""
        # Mock captcha element found
        mock_captcha = MagicMock()
        self.mock_driver_manager.find_element.return_value = mock_captcha
        
        success = await self.login_manager._handle_captcha()
        
        # Should return True even with captcha (basic implementation)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_submit_login_form_success(self):
        """Test successful login form submission."""
        self.mock_driver_manager.click_element.return_value = True
        
        success = await self.login_manager._submit_login_form()
        
        assert success is True
        self.mock_driver_manager.click_element.assert_called()
    
    @pytest.mark.asyncio
    async def test_submit_login_form_no_button_found(self):
        """Test login form submission when no submit button found."""
        self.mock_driver_manager.click_element.return_value = False
        self.mock_driver_manager.find_element.return_value = None
        
        success = await self.login_manager._submit_login_form()
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_submit_login_form_enter_key_fallback(self):
        """Test login form submission using Enter key fallback."""
        # Mock no submit button found, but password field found
        self.mock_driver_manager.click_element.return_value = False
        
        mock_password_element = MagicMock()
        self.mock_driver_manager.find_element.return_value = mock_password_element
        
        success = await self.login_manager._submit_login_form()
        
        assert success is True
        mock_password_element.send_keys.assert_called()
    
    @pytest.mark.asyncio
    async def test_check_login_status_success_indicators(self):
        """Test login status check with success indicators."""
        # Mock successful login indicators
        self.mock_driver_manager.get_current_url.return_value = "https://example.com/dashboard"
        self.mock_driver_manager.find_element.return_value = MagicMock()  # Found logout element
        
        success = await self.login_manager._check_login_status()
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_check_login_status_failure_indicators(self):
        """Test login status check with failure indicators."""
        # Mock failure indicators
        self.mock_driver_manager.get_current_url.return_value = "https://example.com/login?error=1"
        
        success = await self.login_manager._check_login_status()
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_check_login_status_no_clear_indicators(self):
        """Test login status check with no clear indicators."""
        # Mock no clear success or failure indicators
        self.mock_driver_manager.get_current_url.return_value = "https://example.com/page"
        self.mock_driver_manager.find_element.return_value = None
        self.mock_driver_manager.get_page_source.return_value = "normal page content"
        
        success = await self.login_manager._check_login_status()
        
        # Should assume failure when unclear
        assert success is False
    
    @pytest.mark.asyncio
    async def test_try_cookie_login_success(self):
        """Test successful cookie-based login."""
        # Mock cookies available
        self.login_manager._session_cookies = [
            {'name': 'session', 'value': 'abc123', 'domain': 'example.com'}
        ]
        
        # Mock successful cookie login
        with patch.object(self.login_manager, 'load_cookies', return_value=True):
            with patch.object(self.login_manager, '_check_login_status', return_value=True):
                success = await self.login_manager._try_cookie_login("https://example.com/login")
        
        assert success is True
        self.mock_driver.add_cookie.assert_called()
        self.mock_driver.refresh.assert_called()
    
    @pytest.mark.asyncio
    async def test_try_cookie_login_no_cookies(self):
        """Test cookie login when no cookies available."""
        with patch.object(self.login_manager, 'load_cookies', return_value=False):
            success = await self.login_manager._try_cookie_login("https://example.com/login")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_try_cookie_login_cookies_invalid(self):
        """Test cookie login when cookies are invalid."""
        with patch.object(self.login_manager, 'load_cookies', return_value=True):
            with patch.object(self.login_manager, '_check_login_status', return_value=False):
                success = await self.login_manager._try_cookie_login("https://example.com/login")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_login_success_fresh(self):
        """Test successful fresh login."""
        # Mock failed cookie login, successful fresh login
        with patch.object(self.login_manager, '_try_cookie_login', return_value=False):
            with patch.object(self.login_manager, '_perform_fresh_login', return_value=True):
                with patch.object(self.login_manager, 'save_cookies', return_value=True):
                    success = await self.login_manager.login("https://example.com/login")
        
        assert success is True
        assert self.login_manager._is_logged_in is True
        assert self.login_manager._login_attempts == 0  # Reset on success
    
    @pytest.mark.asyncio
    async def test_login_success_cookies(self):
        """Test successful cookie-based login."""
        with patch.object(self.login_manager, '_try_cookie_login', return_value=True):
            success = await self.login_manager.login("https://example.com/login")
        
        assert success is True
        assert self.login_manager._is_logged_in is True
    
    @pytest.mark.asyncio
    async def test_login_failure(self):
        """Test login failure."""
        with patch.object(self.login_manager, '_try_cookie_login', return_value=False):
            with patch.object(self.login_manager, '_perform_fresh_login', return_value=False):
                success = await self.login_manager.login("https://example.com/login")
        
        assert success is False
        assert self.login_manager._is_logged_in is False
    
    @pytest.mark.asyncio
    async def test_login_cooldown_blocked(self):
        """Test login blocked by cooldown."""
        # Set recent failed attempt
        self.login_manager._last_login_attempt = datetime.now()
        self.login_manager._login_attempts = 1
        
        success = await self.login_manager.login("https://example.com/login")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_is_logged_in_cached(self):
        """Test is_logged_in with cached status."""
        self.login_manager._is_logged_in = True
        self.login_manager._last_login_check = datetime.now()
        
        result = await self.login_manager.is_logged_in()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_logged_in_refresh_needed(self):
        """Test is_logged_in when refresh is needed."""
        self.login_manager._last_login_check = datetime.now() - timedelta(seconds=400)
        
        with patch.object(self.login_manager, '_check_login_status', return_value=True):
            result = await self.login_manager.is_logged_in()
        
        assert result is True
        assert self.login_manager._last_login_check is not None
    
    def test_should_check_login_status_no_previous_check(self):
        """Test should check login status when no previous check."""
        assert self.login_manager._should_check_login_status() is True
    
    def test_should_check_login_status_recent_check(self):
        """Test should check login status with recent check."""
        self.login_manager._last_login_check = datetime.now()
        assert self.login_manager._should_check_login_status() is False
    
    def test_should_check_login_status_old_check(self):
        """Test should check login status with old check."""
        self.login_manager._last_login_check = datetime.now() - timedelta(seconds=400)
        assert self.login_manager._should_check_login_status() is True
    
    @pytest.mark.asyncio
    async def test_refresh_session_success(self):
        """Test successful session refresh."""
        with patch.object(self.login_manager, '_check_login_status', return_value=True):
            with patch.object(self.login_manager, 'save_cookies', return_value=True):
                success = await self.login_manager.refresh_session()
        
        assert success is True
        self.mock_driver.refresh.assert_called()
    
    @pytest.mark.asyncio
    async def test_refresh_session_failure(self):
        """Test session refresh failure."""
        with patch.object(self.login_manager, '_check_login_status', return_value=False):
            success = await self.login_manager.refresh_session()
        
        assert success is False
        assert self.login_manager._is_logged_in is False
    
    def test_reset_login_attempts(self):
        """Test resetting login attempts."""
        self.login_manager._login_attempts = 3
        self.login_manager._last_login_attempt = datetime.now()
        
        self.login_manager.reset_login_attempts()
        
        assert self.login_manager._login_attempts == 0
        assert self.login_manager._last_login_attempt is None
    
    def test_get_login_stats(self):
        """Test getting login statistics."""
        self.login_manager._is_logged_in = True
        self.login_manager._login_attempts = 2
        self.login_manager._last_login_check = datetime.now()
        self.login_manager._session_cookies = [{'name': 'test'}]
        
        stats = self.login_manager.get_login_stats()
        
        assert stats['is_logged_in'] is True
        assert stats['login_attempts'] == 2
        assert stats['max_attempts'] == 3
        assert stats['cookies_count'] == 1
        assert stats['cookies_file'] == self.temp_cookies.name
        assert 'last_login_check' in stats
        assert 'last_login_attempt' in stats