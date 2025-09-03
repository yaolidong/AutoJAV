#!/usr/bin/env python3
"""
Manages JAVDB login process inside a VNC environment.
"""

import os
import logging
import time
import json
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class VNCLoginManager:
    def __init__(self, config_dir="/app/config"):
        self.config_dir = Path(config_dir)
        self.cookie_file = self.config_dir / "javdb_cookies.json"
        self.login_url = "https://javdb.com/login"
        self.driver = None

    def start_login_session(self):
        """Starts a browser in the VNC session for the user to log in."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

        try:
            os.environ["DISPLAY"] = ":1"
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1280,800")
            # Add user data dir for persistence
            chrome_options.add_argument("--user-data-dir=/app/config/chrome_vnc_profile")

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.get(self.login_url)

            logger.info("Browser started in VNC session for JAVDB login.")
            return {
                "success": True,
                "message": "Browser started. Please connect via VNC.",
                "vnc_url": "vnc://<your-host-ip>:5901",
                "web_vnc_url": "http://<your-host-ip>:6901"
            }
        except Exception as e:
            logger.error(f"Failed to start browser in VNC: {e}")
            return {"success": False, "error": str(e)}

    def check_and_save_cookies(self):
        """Checks if login is complete and saves cookies."""
        if not self.driver:
            return {"success": False, "error": "Browser not started."}

        try:
            # Check for logout link, indicating a successful login
            logout_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/logout')]")
            if logout_elements:
                logger.info("Login successful, saving cookies.")
                cookies = self.driver.get_cookies()
                self._save_cookies_to_file(cookies)
                self.driver.quit()
                self.driver = None
                return {"success": True, "message": "Cookies saved successfully."}
            else:
                logger.info("Login not yet complete.")
                return {"success": False, "error": "Login not complete."}
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return {"success": False, "error": str(e)}

    def _save_cookies_to_file(self, cookies):
        """Saves cookies to the specified file."""
        cookie_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "domain": "https://javdb.com"
        }
        with open(self.cookie_file, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        self.cookie_file.chmod(0o600)
        logger.info(f"Saved {len(cookies)} cookies to {self.cookie_file}")
