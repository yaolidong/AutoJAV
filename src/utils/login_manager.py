"""Login manager for handling website authentication."""

import json
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .webdriver_manager import WebDriverManager


class LoginManager:
    """Manages website login and session persistence."""

    def __init__(
        self,
        username: str,
        password: str,
        driver_manager: WebDriverManager,
        cookies_file: Optional[str] = None,
    ):
        """
        Initialize the login manager.

        Args:
            username: Login username
            password: Login password
            driver_manager: WebDriver manager instance
            cookies_file: Path to save/load cookies
        """
        self.username = username
        self.password = password
        self.driver_manager = driver_manager
        self.cookies_file = cookies_file or "cookies.json"
        self.logger = logging.getLogger(__name__)

        # Login state
        self._is_logged_in = False
        self._last_login_check = None
        self._login_check_interval = 300  # 5 minutes
        self._session_cookies: List[Dict] = []

        # Login attempt tracking
        self._login_attempts = 0
        self._max_login_attempts = 3
        self._last_login_attempt = None
        self._login_cooldown = 60  # 1 minute between attempts

    async def login(self, login_url: str, **kwargs) -> bool:
        """
        Perform login to the website.

        Args:
            login_url: URL of the login page
            **kwargs: Additional login parameters

        Returns:
            True if login successful, False otherwise
        """
        # Check cooldown
        if not self._can_attempt_login():
            self.logger.warning("Login attempt blocked due to cooldown")
            return False

        self._last_login_attempt = datetime.now()
        self._login_attempts += 1

        try:
            self.logger.info(f"Attempting login to {login_url}")

            # Try to load existing cookies first
            if await self._try_cookie_login(login_url):
                return True

            # Perform fresh login
            success = await self._perform_fresh_login(login_url, **kwargs)

            if success:
                self._is_logged_in = True
                self._last_login_check = datetime.now()
                self._login_attempts = 0  # Reset on success
                await self.save_cookies()
                self.logger.info("Login successful")
            else:
                self.logger.error("Login failed")

            return success

        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False

    def _can_attempt_login(self) -> bool:
        """
        Check if login attempt is allowed based on cooldown and max attempts.

        Returns:
            True if login attempt is allowed
        """
        if self._login_attempts >= self._max_login_attempts:
            self.logger.error(
                f"Maximum login attempts ({self._max_login_attempts}) exceeded"
            )
            return False

        if self._last_login_attempt:
            time_since_last = datetime.now() - self._last_login_attempt
            if time_since_last.total_seconds() < self._login_cooldown:
                remaining = self._login_cooldown - time_since_last.total_seconds()
                self.logger.warning(
                    f"Login cooldown active, {remaining:.0f}s remaining"
                )
                return False

        return True

    async def _try_cookie_login(self, login_url: str) -> bool:
        """
        Try to login using saved cookies.

        Args:
            login_url: URL to test login with cookies

        Returns:
            True if cookie login successful
        """
        try:
            # Load cookies from file
            if not await self.load_cookies():
                return False

            # Navigate to login page
            if not self.driver_manager.get_page(login_url):
                return False

            # Add cookies to browser
            for cookie in self._session_cookies:
                try:
                    self.driver_manager.driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"Failed to add cookie: {e}")

            # Refresh page to apply cookies
            self.driver_manager.driver.refresh()
            await asyncio.sleep(2)

            # Check if login was successful
            if await self._check_login_status():
                self.logger.info("Cookie login successful")
                return True

        except Exception as e:
            self.logger.debug(f"Cookie login failed: {e}")

        return False

    async def _perform_fresh_login(self, login_url: str, **kwargs) -> bool:
        """
        Perform fresh login with username and password.

        Args:
            login_url: URL of the login page
            **kwargs: Additional login parameters

        Returns:
            True if login successful
        """
        try:
            # Navigate to login page
            if not self.driver_manager.get_page(login_url):
                return False

            # Wait for login form
            await asyncio.sleep(2)

            # Fill login form
            if not await self._fill_login_form(**kwargs):
                return False

            # Handle captcha if present
            if not await self._handle_captcha():
                return False

            # Submit login form
            if not await self._submit_login_form():
                return False

            # Wait for login to complete
            await asyncio.sleep(3)

            # Check login status
            return await self._check_login_status()

        except Exception as e:
            self.logger.error(f"Fresh login failed: {e}")
            return False

    async def _fill_login_form(self, **kwargs) -> bool:
        """
        Fill the login form with credentials.

        Args:
            **kwargs: Additional form parameters

        Returns:
            True if form filled successfully
        """
        # Common username field selectors
        username_selectors = [
            'input[name="username"]',
            'input[name="email"]',
            'input[name="user"]',
            'input[type="email"]',
            "#username",
            "#email",
            "#user",
            ".username",
            ".email",
        ]

        # Common password field selectors
        password_selectors = [
            'input[name="password"]',
            'input[type="password"]',
            "#password",
            ".password",
        ]

        # Fill username
        username_filled = False
        for selector in username_selectors:
            if self.driver_manager.send_keys(selector, self.username):
                username_filled = True
                self.logger.debug(f"Username filled using selector: {selector}")
                break

        if not username_filled:
            self.logger.error("Could not find username field")
            return False

        # Fill password
        password_filled = False
        for selector in password_selectors:
            if self.driver_manager.send_keys(selector, self.password):
                password_filled = True
                self.logger.debug(f"Password filled using selector: {selector}")
                break

        if not password_filled:
            self.logger.error("Could not find password field")
            return False

        return True

    async def _handle_captcha(self) -> bool:
        """
        Handle captcha if present on the login page.

        Returns:
            True if captcha handled or not present
        """
        # Common captcha selectors
        captcha_selectors = [
            'img[src*="captcha"]',
            'img[alt*="captcha"]',
            ".captcha img",
            "#captcha img",
            'img[src*="verify"]',
            'img[src*="code"]',
        ]

        # Check if captcha is present
        captcha_present = False
        for selector in captcha_selectors:
            if self.driver_manager.find_element(selector):
                captcha_present = True
                self.logger.warning(f"Captcha detected: {selector}")
                break

        if not captcha_present:
            return True

        # For now, we'll implement a basic captcha handling strategy
        # In a real implementation, you might want to:
        # 1. Use OCR to read the captcha
        # 2. Use a captcha solving service
        # 3. Wait for manual input
        # 4. Try to bypass captcha

        self.logger.warning("Captcha detected but not handled - login may fail")

        # Wait a bit to see if captcha disappears or can be bypassed
        await asyncio.sleep(5)

        return True

    async def _submit_login_form(self) -> bool:
        """
        Submit the login form.

        Returns:
            True if form submitted successfully
        """
        # Common submit button selectors
        submit_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            'button[name="login"]',
            'button[name="submit"]',
            ".login-button",
            ".submit-button",
            "#login-button",
            "#submit-button",
            "form button",
            'input[value*="登录"]',
            'input[value*="Login"]',
            'button:contains("登录")',
            'button:contains("Login")',
        ]

        # Try to click submit button
        for selector in submit_selectors:
            if self.driver_manager.click_element(selector):
                self.logger.debug(f"Login form submitted using: {selector}")
                return True

        # If no submit button found, try pressing Enter on password field
        password_selectors = ['input[type="password"]', "#password"]
        for selector in password_selectors:
            element = self.driver_manager.find_element(selector)
            if element:
                try:
                    from selenium.webdriver.common.keys import Keys

                    element.send_keys(Keys.RETURN)
                    self.logger.debug("Login form submitted using Enter key")
                    return True
                except Exception as e:
                    self.logger.debug(f"Failed to submit with Enter: {e}")

        self.logger.error("Could not find submit button or submit form")
        return False

    async def _check_login_status(self) -> bool:
        """
        Check if login was successful.

        Returns:
            True if logged in
        """
        # Wait for page to load after login
        await asyncio.sleep(3)

        current_url = self.driver_manager.get_current_url()

        # Check for login success indicators
        success_indicators = [
            # URL changes
            lambda: "login" not in current_url.lower(),
            lambda: "dashboard" in current_url.lower(),
            lambda: "profile" in current_url.lower(),
            lambda: "user" in current_url.lower(),
            # Page elements
            lambda: self.driver_manager.find_element(".user-menu") is not None,
            lambda: self.driver_manager.find_element(".logout") is not None,
            lambda: self.driver_manager.find_element("#logout") is not None,
            lambda: self.driver_manager.find_element('a[href*="logout"]') is not None,
        ]

        # Check for login failure indicators
        failure_indicators = [
            # Error messages
            lambda: self.driver_manager.find_element(".error") is not None,
            lambda: self.driver_manager.find_element(".alert-error") is not None,
            lambda: self.driver_manager.find_element('[class*="error"]') is not None,
            lambda: "error" in current_url.lower(),
            lambda: "invalid" in self.driver_manager.get_page_source().lower(),
        ]

        # Check failure indicators first
        for indicator in failure_indicators:
            try:
                if indicator():
                    self.logger.debug("Login failure indicator detected")
                    return False
            except Exception:
                pass

        # Check success indicators
        for indicator in success_indicators:
            try:
                if indicator():
                    self.logger.debug("Login success indicator detected")
                    return True
            except Exception:
                pass

        # If no clear indicators, assume failure
        self.logger.warning("Could not determine login status clearly")
        return False

    async def is_logged_in(self) -> bool:
        """
        Check if currently logged in.

        Returns:
            True if logged in
        """
        # Check if we need to refresh login status
        if self._should_check_login_status():
            self._is_logged_in = await self._check_login_status()
            self._last_login_check = datetime.now()

        return self._is_logged_in

    def _should_check_login_status(self) -> bool:
        """
        Check if login status should be refreshed.

        Returns:
            True if status check is needed
        """
        if self._last_login_check is None:
            return True

        time_since_check = datetime.now() - self._last_login_check
        return time_since_check.total_seconds() > self._login_check_interval

    async def refresh_session(self) -> bool:
        """
        Refresh the login session.

        Returns:
            True if session refreshed successfully
        """
        try:
            # Navigate to a page that requires login
            current_url = self.driver_manager.get_current_url()
            self.driver_manager.driver.refresh()
            await asyncio.sleep(2)

            # Check if still logged in
            if await self._check_login_status():
                await self.save_cookies()
                return True
            else:
                self._is_logged_in = False
                return False

        except Exception as e:
            self.logger.error(f"Session refresh failed: {e}")
            return False

    async def save_cookies(self) -> bool:
        """
        Save current session cookies to file.

        Returns:
            True if cookies saved successfully
        """
        try:
            cookies = self.driver_manager.driver.get_cookies()

            # Filter out expired cookies
            valid_cookies = []
            current_time = time.time()

            for cookie in cookies:
                # Check if cookie has expiry and is not expired
                if "expiry" in cookie:
                    if cookie["expiry"] > current_time:
                        valid_cookies.append(cookie)
                else:
                    # Session cookies (no expiry)
                    valid_cookies.append(cookie)

            self._session_cookies = valid_cookies

            # Save to file
            cookies_path = Path(self.cookies_file)
            cookies_path.parent.mkdir(parents=True, exist_ok=True)

            with open(cookies_path, "w") as f:
                json.dump(valid_cookies, f, indent=2)

            self.logger.debug(
                f"Saved {len(valid_cookies)} cookies to {self.cookies_file}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")
            return False

    async def load_cookies(self) -> bool:
        """
        Load session cookies from file.

        Returns:
            True if cookies loaded successfully
        """
        try:
            cookies_path = Path(self.cookies_file)

            if not cookies_path.exists():
                self.logger.debug("No cookies file found")
                return False

            with open(cookies_path, "r") as f:
                cookies = json.load(f)

            # Filter out expired cookies
            valid_cookies = []
            current_time = time.time()

            for cookie in cookies:
                if "expiry" in cookie:
                    if cookie["expiry"] > current_time:
                        valid_cookies.append(cookie)
                else:
                    valid_cookies.append(cookie)

            self._session_cookies = valid_cookies

            self.logger.debug(
                f"Loaded {len(valid_cookies)} cookies from {self.cookies_file}"
            )
            return len(valid_cookies) > 0

        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")
            return False

    def clear_cookies(self):
        """Clear saved cookies."""
        try:
            cookies_path = Path(self.cookies_file)
            if cookies_path.exists():
                cookies_path.unlink()
            self._session_cookies = []
            self.logger.debug("Cookies cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear cookies: {e}")

    def reset_login_attempts(self):
        """Reset login attempt counter."""
        self._login_attempts = 0
        self._last_login_attempt = None
        self.logger.debug("Login attempts reset")

    def get_login_stats(self) -> Dict[str, Any]:
        """
        Get login statistics.

        Returns:
            Dictionary with login statistics
        """
        return {
            "is_logged_in": self._is_logged_in,
            "login_attempts": self._login_attempts,
            "max_attempts": self._max_login_attempts,
            "last_login_check": self._last_login_check.isoformat()
            if self._last_login_check
            else None,
            "last_login_attempt": self._last_login_attempt.isoformat()
            if self._last_login_attempt
            else None,
            "cookies_count": len(self._session_cookies),
            "cookies_file": self.cookies_file,
        }
