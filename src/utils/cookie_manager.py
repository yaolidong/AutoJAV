"""
Cookie Manager for persistent authentication
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pickle

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class CookieManager:
    """
    Manages browser cookies for persistent authentication across sessions.
    """
    
    def __init__(self, cookie_dir: Optional[Path] = None):
        """
        Initialize cookie manager.
        
        Args:
            cookie_dir: Directory to store cookie files
        """
        self.cookie_dir = cookie_dir or Path.home() / '.autojav' / 'cookies'
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_cookies(self, driver: webdriver.Chrome, domain: str) -> bool:
        """
        Save cookies from current browser session.
        
        Args:
            driver: Selenium WebDriver instance
            domain: Domain name for cookie file
            
        Returns:
            True if cookies saved successfully
        """
        try:
            cookies = driver.get_cookies()
            
            if not cookies:
                self.logger.warning(f"No cookies to save for {domain}")
                return False
            
            # Save as JSON for readability
            cookie_file = self.cookie_dir / f"{domain}_cookies.json"
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, default=str)
            
            # Also save as pickle for compatibility
            pickle_file = self.cookie_dir / f"{domain}_cookies.pkl"
            with open(pickle_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            self.logger.info(f"Saved {len(cookies)} cookies for {domain}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save cookies for {domain}: {e}")
            return False
    
    def load_cookies(self, driver: webdriver.Chrome, domain: str) -> bool:
        """
        Load cookies into browser session.
        
        Args:
            driver: Selenium WebDriver instance
            domain: Domain name for cookie file
            
        Returns:
            True if cookies loaded successfully
        """
        try:
            # Try JSON file first
            cookie_file = self.cookie_dir / f"{domain}_cookies.json"
            pickle_file = self.cookie_dir / f"{domain}_cookies.pkl"
            
            cookies = None
            
            if cookie_file.exists():
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Failed to load JSON cookies: {e}")
            
            # Fallback to pickle file
            if cookies is None and pickle_file.exists():
                try:
                    with open(pickle_file, 'rb') as f:
                        cookies = pickle.load(f)
                except Exception as e:
                    self.logger.warning(f"Failed to load pickle cookies: {e}")
            
            if not cookies:
                self.logger.info(f"No saved cookies found for {domain}")
                return False
            
            # Navigate to domain first (required for adding cookies)
            current_url = driver.current_url
            if domain not in current_url:
                driver.get(f"https://{domain}")
            
            # Add cookies
            for cookie in cookies:
                # Remove expiry if it's in the past
                if 'expiry' in cookie:
                    if cookie['expiry'] < datetime.now().timestamp():
                        continue
                
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"Failed to add cookie: {e}")
            
            self.logger.info(f"Loaded {len(cookies)} cookies for {domain}")
            
            # Refresh page to apply cookies
            driver.refresh()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cookies for {domain}: {e}")
            return False
    
    def clear_cookies(self, domain: str) -> bool:
        """
        Clear saved cookies for a domain.
        
        Args:
            domain: Domain name
            
        Returns:
            True if cookies cleared successfully
        """
        try:
            cookie_file = self.cookie_dir / f"{domain}_cookies.json"
            pickle_file = self.cookie_dir / f"{domain}_cookies.pkl"
            
            removed = False
            
            if cookie_file.exists():
                cookie_file.unlink()
                removed = True
            
            if pickle_file.exists():
                pickle_file.unlink()
                removed = True
            
            if removed:
                self.logger.info(f"Cleared cookies for {domain}")
            
            return removed
            
        except Exception as e:
            self.logger.error(f"Failed to clear cookies for {domain}: {e}")
            return False
    
    def get_cookie_age(self, domain: str) -> Optional[timedelta]:
        """
        Get age of saved cookies.
        
        Args:
            domain: Domain name
            
        Returns:
            Age of cookies or None if not found
        """
        try:
            cookie_file = self.cookie_dir / f"{domain}_cookies.json"
            
            if not cookie_file.exists():
                return None
            
            mtime = datetime.fromtimestamp(cookie_file.stat().st_mtime)
            age = datetime.now() - mtime
            
            return age
            
        except Exception as e:
            self.logger.error(f"Failed to get cookie age for {domain}: {e}")
            return None
    
    def are_cookies_valid(self, domain: str, max_age_days: int = 30) -> bool:
        """
        Check if saved cookies are still valid (not too old).
        
        Args:
            domain: Domain name
            max_age_days: Maximum age in days before cookies are considered invalid
            
        Returns:
            True if cookies exist and are not too old
        """
        age = self.get_cookie_age(domain)
        
        if age is None:
            return False
        
        return age.days < max_age_days


class JavDBAuthManager:
    """
    Manages JavDB authentication with cookie persistence.
    """
    
    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        """
        Initialize JavDB auth manager.
        
        Args:
            cookie_manager: Cookie manager instance
        """
        self.cookie_manager = cookie_manager or CookieManager()
        self.logger = logging.getLogger(__name__)
        self.domain = "javdb.com"
    
    def login_with_cookies(self, driver: webdriver.Chrome) -> bool:
        """
        Try to login using saved cookies.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if login successful
        """
        try:
            # Load cookies
            if not self.cookie_manager.load_cookies(driver, self.domain):
                self.logger.info("No saved cookies for JavDB")
                return False
            
            # Navigate to a protected page to verify login
            driver.get(f"https://{self.domain}/users")
            
            # Wait and check if we're logged in
            wait = WebDriverWait(driver, 10)
            
            try:
                # Check for user menu or other login indicator
                user_menu = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "user-menu"))
                )
                
                if user_menu:
                    self.logger.info("Successfully logged in to JavDB with cookies")
                    return True
                    
            except TimeoutException:
                self.logger.info("Cookie login failed - login required")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during cookie login: {e}")
            return False
    
    def manual_login_prompt(self, driver: webdriver.Chrome, timeout: int = 300) -> bool:
        """
        Prompt user to manually login and wait for completion.
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Maximum time to wait for login in seconds
            
        Returns:
            True if login successful
        """
        try:
            # Navigate to login page
            driver.get(f"https://{self.domain}/login")
            
            self.logger.info("=" * 60)
            self.logger.info("MANUAL LOGIN REQUIRED")
            self.logger.info("Please login to JavDB in the browser window")
            self.logger.info("Complete any CAPTCHA if required")
            self.logger.info(f"Waiting up to {timeout} seconds...")
            self.logger.info("=" * 60)
            
            # Wait for login completion
            wait = WebDriverWait(driver, timeout)
            
            try:
                # Wait for redirect away from login page or user menu to appear
                wait.until(
                    lambda d: "login" not in d.current_url.lower() or 
                    d.find_elements(By.CLASS_NAME, "user-menu")
                )
                
                # Verify login success
                if "login" not in driver.current_url.lower():
                    self.logger.info("Login successful!")
                    
                    # Save cookies for future use
                    self.cookie_manager.save_cookies(driver, self.domain)
                    
                    return True
                else:
                    self.logger.warning("Login appears to have failed")
                    return False
                    
            except TimeoutException:
                self.logger.error("Login timeout - please try again")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during manual login: {e}")
            return False
    
    def ensure_logged_in(self, driver: webdriver.Chrome) -> bool:
        """
        Ensure user is logged in, using cookies or prompting for manual login.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if logged in successfully
        """
        # First try cookie login
        if self.cookie_manager.are_cookies_valid(self.domain):
            if self.login_with_cookies(driver):
                return True
        
        # If cookie login fails, prompt for manual login
        self.logger.info("Cookie login failed or cookies expired")
        return self.manual_login_prompt(driver)
    
    def logout(self, driver: webdriver.Chrome) -> bool:
        """
        Logout and clear saved cookies.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if logout successful
        """
        try:
            # Navigate to logout URL
            driver.get(f"https://{self.domain}/logout")
            
            # Clear saved cookies
            self.cookie_manager.clear_cookies(self.domain)
            
            self.logger.info("Logged out and cleared cookies")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False