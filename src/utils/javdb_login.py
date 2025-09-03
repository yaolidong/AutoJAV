#!/usr/bin/env python3
"""
JavDB Manual Login and Cookie Manager
Handles manual login to JavDB and saves cookies for reuse
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

class JavDBLoginManager:
    """Manages JavDB login and cookie persistence"""
    
    def __init__(self, config_dir: str = "/app/config", user_data_dir: str = "config/chrome_profile"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.config_dir / "javdb_cookies.json"
        self.user_data_dir = user_data_dir
        self.base_url = "https://javdb.com"
        self.login_url = "https://javdb.com/login"
        
    def manual_login(self, headless: bool = False, timeout: int = 300) -> bool:
        """
        Open browser for manual login to JavDB
        
        Args:
            headless: Whether to run browser in headless mode (False for manual login)
            timeout: Maximum time to wait for login (seconds)
            
        Returns:
            True if login successful and cookies saved
        """
        driver = None
        try:
            # Setup Chrome options
            chrome_options = Options()
            if not headless:
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                # Set window size for better visibility
                chrome_options.add_argument("--window-size=1280,800")
            else:
                chrome_options.add_argument("--headless")

            if self.user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
                logger.info(f"Using persistent user profile: {self.user_data_dir}")
                
            # Add user agent to appear more like a real browser
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            logger.info("Starting Chrome browser for JavDB login...")
            driver = webdriver.Chrome(options=chrome_options)
            
            # Navigate to login page
            logger.info(f"Navigating to {self.login_url}")
            driver.get(self.login_url)
            
            print("\n" + "="*60)
            print("JavDB Manual Login")
            print("="*60)
            print("Please login to JavDB in the opened browser window.")
            print("The script will wait for you to complete the login.")
            print(f"Timeout: {timeout} seconds")
            print("="*60 + "\n")
            
            # Wait for user to login (check for login success indicators)
            start_time = time.time()
            logged_in = False
            
            while not logged_in and (time.time() - start_time) < timeout:
                try:
                    # Check if we're logged in by looking for user menu or logout button
                    # Adjust these selectors based on actual JavDB logged-in indicators
                    current_url = driver.current_url
                    
                    # Check if redirected away from login page
                    if "/login" not in current_url:
                        # Try to find user menu or profile elements
                        user_elements = driver.find_elements(By.CSS_SELECTOR, ".user-menu, .avatar, [href*='/users/'], [href*='/logout']")
                        if user_elements:
                            logged_in = True
                            logger.info("Login detected! Saving cookies...")
                            break
                    
                    # Also check for specific logged-in elements
                    if driver.find_elements(By.XPATH, "//a[contains(@href, '/logout')]"):
                        logged_in = True
                        logger.info("Logout link found - user is logged in!")
                        break
                        
                except Exception as e:
                    logger.debug(f"Checking login status: {e}")
                
                time.sleep(2)  # Check every 2 seconds
                remaining = int(timeout - (time.time() - start_time))
                if remaining % 10 == 0 and remaining > 0:
                    print(f"Waiting for login... {remaining} seconds remaining")
            
            if not logged_in:
                logger.error("Login timeout - no login detected")
                return False
            
            # Save cookies
            cookies = driver.get_cookies()
            if self.save_cookies(cookies):
                print("\n✅ Login successful! Cookies saved.")
                logger.info(f"Saved {len(cookies)} cookies to {self.cookie_file}")
                
                # Verify cookies work
                if self.verify_cookies(driver):
                    print("✅ Cookies verified - you can now use JavDB scraping!")
                    return True
                else:
                    logger.warning("Cookie verification failed")
                    return False
            else:
                logger.error("Failed to save cookies")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
        finally:
            if driver:
                driver.quit()
    
    def save_cookies(self, cookies: List[Dict]) -> bool:
        """Save cookies to file"""
        try:
            cookie_data = {
                "cookies": cookies,
                "timestamp": datetime.now().isoformat(),
                "domain": self.base_url
            }
            
            with open(self.cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            # Set appropriate permissions
            self.cookie_file.chmod(0o600)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    def load_cookies(self) -> Optional[List[Dict]]:
        """Load cookies from file"""
        try:
            if not self.cookie_file.exists():
                logger.warning("Cookie file does not exist")
                return None
                
            with open(self.cookie_file, 'r') as f:
                cookie_data = json.load(f)
            
            # Check if cookies are not too old (e.g., 30 days)
            timestamp = datetime.fromisoformat(cookie_data.get("timestamp", ""))
            if datetime.now() - timestamp > timedelta(days=30):
                logger.warning("Cookies are older than 30 days, may need re-login")
            
            return cookie_data.get("cookies", [])
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return None
    
    def verify_cookies(self, driver=None) -> bool:
        """Verify that saved cookies work"""
        close_driver = False
        
        try:
            if not driver:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                if self.user_data_dir:
                    chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
                driver = webdriver.Chrome(options=chrome_options)
                close_driver = True
            
            # Load main page
            driver.get(self.base_url)
            
            # Add saved cookies
            cookies = self.load_cookies()
            if not cookies:
                return False
                
            for cookie in cookies:
                # Selenium requires certain format
                if 'sameSite' in cookie and cookie['sameSite'] == 'None':
                    cookie['sameSite'] = 'Lax'
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie: {e}")
            
            # Refresh page with cookies
            driver.refresh()
            time.sleep(2)
            
            # Check if logged in
            logged_in_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/logout')]")
            return len(logged_in_elements) > 0
            
        except Exception as e:
            logger.error(f"Cookie verification error: {e}")
            return False
        finally:
            if close_driver and driver:
                driver.quit()
    
    def clear_cookies(self) -> bool:
        """Clear saved cookies"""
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                logger.info("Cookies cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")
            return False
    
    def get_cookie_status(self) -> Dict:
        """Get current cookie status"""
        if not self.cookie_file.exists():
            return {
                "exists": False,
                "valid": False,
                "message": "No cookies saved"
            }
        
        try:
            with open(self.cookie_file, 'r') as f:
                cookie_data = json.load(f)
            
            timestamp = datetime.fromisoformat(cookie_data.get("timestamp", ""))
            age_days = (datetime.now() - timestamp).days
            
            return {
                "exists": True,
                "timestamp": cookie_data.get("timestamp"),
                "age_days": age_days,
                "cookie_count": len(cookie_data.get("cookies", [])),
                "valid": age_days < 30,
                "message": f"Cookies saved {age_days} days ago"
            }
        except Exception as e:
            return {
                "exists": True,
                "valid": False,
                "error": str(e),
                "message": "Error reading cookies"
            }


def main():
    """Main function for standalone usage"""
    import argparse
    import sys
    from src.utils.logging_config import setup_application_logging
    
    setup_application_logging()
    
    parser = argparse.ArgumentParser(description='JavDB Login Manager')
    parser.add_argument('--login', action='store_true', help='Perform manual login')
    parser.add_argument('--verify', action='store_true', help='Verify saved cookies')
    parser.add_argument('--status', action='store_true', help='Check cookie status')
    parser.add_argument('--clear', action='store_true', help='Clear saved cookies')
    parser.add_argument('--config-dir', default='/app/config', help='Config directory path')
    parser.add_argument('--user-data-dir', default='config/chrome_profile', help='Persistent user data directory for Chrome')
    
    args = parser.parse_args()
    
    manager = JavDBLoginManager(config_dir=args.config_dir, user_data_dir=args.user_data_dir)
    
    if args.login:
        success = manager.manual_login(headless=False)
        sys.exit(0 if success else 1)
    
    elif args.verify:
        valid = manager.verify_cookies()
        if valid:
            print("✅ Cookies are valid")
        else:
            print("❌ Cookies are invalid or expired")
        sys.exit(0 if valid else 1)
    
    elif args.status:
        status = manager.get_cookie_status()
        print("\nCookie Status:")
        print("-" * 40)
        for key, value in status.items():
            print(f"{key}: {value}")
        sys.exit(0)
    
    elif args.clear:
        if manager.clear_cookies():
            print("✅ Cookies cleared")
        else:
            print("❌ Failed to clear cookies")
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()