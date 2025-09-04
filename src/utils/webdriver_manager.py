"""WebDriver manager for browser automation."""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    WebDriverException, TimeoutException, NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager


class WebDriverManager:
    """Manages Chrome WebDriver instances for web scraping."""
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        proxy_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        window_size: tuple = (1920, 1080)
    ):
        """
        Initialize the WebDriver manager.
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for operations
            proxy_url: Proxy URL for browser
            user_agent: Custom User-Agent string
            window_size: Browser window size (width, height)
        """
        self.headless = headless
        self.timeout = timeout
        self.proxy_url = proxy_url
        self.user_agent = user_agent
        self.window_size = window_size
        self.logger = logging.getLogger(__name__)
        
        self._driver: Optional[webdriver.Chrome] = None
        self._service: Optional[Service] = None
    
    @property
    def driver(self) -> Optional[webdriver.Chrome]:
        """Get the current WebDriver instance."""
        if self._driver is None:
            self.start_driver()
        return self._driver
    
    def __enter__(self):
        """Context manager entry."""
        self.start_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit_driver()
    
    def _get_chrome_options(self) -> Options:
        """
        Get Chrome options for the WebDriver.
        
        Returns:
            Configured Chrome options
        """
        options = Options()
        
        # Basic options
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        # Removed --disable-web-security as it can cause connection issues
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        # Note: Images and JavaScript are required for JavDB to work properly
        # options.add_argument('--disable-images')  # Don't load images for faster loading
        # options.add_argument('--disable-javascript')  # Disable JS if not needed
        
        # User agent
        if self.user_agent:
            options.add_argument(f'--user-agent={self.user_agent}')
        else:
            # Default user agent
            options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
        
        # Proxy settings
        if self.proxy_url:
            options.add_argument(f'--proxy-server={self.proxy_url}')
        
        # Performance optimizations
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # Disable logging
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Disable automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        return options
    
    def start_driver(self) -> webdriver.Chrome:
        """
        Start the Chrome WebDriver.
        
        Returns:
            Chrome WebDriver instance
            
        Raises:
            WebDriverException: If driver fails to start
        """
        if self._driver is not None:
            self.logger.warning("WebDriver already started")
            return self._driver
        
        try:
            options = self._get_chrome_options()
            
            # Check if we should use Selenium Grid (in Docker environment)
            selenium_grid_url = os.environ.get('SELENIUM_HUB_URL', os.environ.get('SELENIUM_GRID_URL', 'http://selenium-grid:4444/wd/hub'))
            
            # Try to connect to Selenium Grid first
            try:
                self.logger.info(f"Connecting to Selenium Grid at {selenium_grid_url}...")
                self._driver = webdriver.Remote(
                    command_executor=selenium_grid_url,
                    options=options
                )
                self.logger.info("Successfully connected to Selenium Grid")
            except Exception as grid_error:
                self.logger.warning(f"Failed to connect to Selenium Grid: {grid_error}")
                self.logger.info("Falling back to local Chrome driver...")
                
                # Fallback to local Chrome driver
                # Get ChromeDriver path
                if os.path.exists('/usr/local/bin/chromedriver'):
                    # Use system chromedriver (Docker)
                    driver_path = '/usr/local/bin/chromedriver'
                else:
                    # Use webdriver-manager to download
                    driver_path = ChromeDriverManager().install()
                
                self._service = Service(driver_path)
                self._driver = webdriver.Chrome(service=self._service, options=options)
            
            # Set timeouts
            self._driver.implicitly_wait(self.timeout)
            self._driver.set_page_load_timeout(self.timeout)
            
            self.logger.info("WebDriver started successfully")
            return self._driver
            
        except Exception as e:
            self.logger.error(f"Failed to start WebDriver: {e}")
            raise WebDriverException(f"Failed to start WebDriver: {e}")
    
    def quit_driver(self):
        """Quit the WebDriver and clean up resources."""
        if self._driver:
            try:
                self._driver.quit()
                self.logger.info("WebDriver quit successfully")
            except Exception as e:
                self.logger.warning(f"Error quitting WebDriver: {e}")
            finally:
                self._driver = None
        
        if self._service:
            try:
                self._service.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping WebDriver service: {e}")
            finally:
                self._service = None
    
    @property
    def driver(self) -> webdriver.Chrome:
        """
        Get the WebDriver instance.
        
        Returns:
            Chrome WebDriver instance
            
        Raises:
            RuntimeError: If driver is not started
        """
        if self._driver is None:
            raise RuntimeError("WebDriver not started. Call start_driver() first.")
        return self._driver
    
    def get_page(self, url: str, wait_for_element: Optional[str] = None) -> bool:
        """
        Navigate to a page and optionally wait for an element.
        
        Args:
            url: URL to navigate to
            wait_for_element: CSS selector to wait for
            
        Returns:
            True if page loaded successfully, False otherwise
        """
        try:
            self.logger.debug(f"Navigating to: {url}")
            self.driver.get(url)
            
            if wait_for_element:
                self.wait_for_element(wait_for_element)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading page {url}: {e}")
            return False
    
    def wait_for_element(
        self,
        selector: str,
        timeout: Optional[int] = None,
        by: By = By.CSS_SELECTOR
    ) -> Optional[WebElement]:
        """
        Wait for an element to be present and visible.
        
        Args:
            selector: Element selector
            timeout: Timeout in seconds (uses default if None)
            by: Selenium By locator type
            
        Returns:
            WebElement if found, None otherwise
        """
        wait_timeout = timeout or self.timeout
        
        try:
            wait = WebDriverWait(self.driver, wait_timeout)
            element = wait.until(
                EC.presence_of_element_located((by, selector))
            )
            self.logger.debug(f"Found element: {selector}")
            return element
            
        except TimeoutException:
            self.logger.warning(f"Timeout waiting for element: {selector}")
            return None
        except Exception as e:
            self.logger.error(f"Error waiting for element {selector}: {e}")
            return None
    
    def find_element(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR
    ) -> Optional[WebElement]:
        """
        Find an element on the current page.
        
        Args:
            selector: Element selector
            by: Selenium By locator type
            
        Returns:
            WebElement if found, None otherwise
        """
        try:
            element = self.driver.find_element(by, selector)
            return element
        except NoSuchElementException:
            self.logger.debug(f"Element not found: {selector}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {selector}: {e}")
            return None
    
    def find_elements(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR
    ) -> List[WebElement]:
        """
        Find multiple elements on the current page.
        
        Args:
            selector: Element selector
            by: Selenium By locator type
            
        Returns:
            List of WebElements (empty if none found)
        """
        try:
            elements = self.driver.find_elements(by, selector)
            return elements
        except Exception as e:
            self.logger.error(f"Error finding elements {selector}: {e}")
            return []
    
    def click_element(self, selector: str, by: By = By.CSS_SELECTOR) -> bool:
        """
        Click an element.
        
        Args:
            selector: Element selector
            by: Selenium By locator type
            
        Returns:
            True if clicked successfully, False otherwise
        """
        element = self.find_element(selector, by)
        if element:
            try:
                element.click()
                self.logger.debug(f"Clicked element: {selector}")
                return True
            except Exception as e:
                self.logger.error(f"Error clicking element {selector}: {e}")
        return False
    
    def send_keys(self, selector: str, text: str, by: By = By.CSS_SELECTOR) -> bool:
        """
        Send keys to an element.
        
        Args:
            selector: Element selector
            text: Text to send
            by: Selenium By locator type
            
        Returns:
            True if successful, False otherwise
        """
        element = self.find_element(selector, by)
        if element:
            try:
                element.clear()
                element.send_keys(text)
                self.logger.debug(f"Sent keys to element: {selector}")
                return True
            except Exception as e:
                self.logger.error(f"Error sending keys to element {selector}: {e}")
        return False
    
    def get_text(self, selector: str, by: By = By.CSS_SELECTOR) -> Optional[str]:
        """
        Get text content of an element.
        
        Args:
            selector: Element selector
            by: Selenium By locator type
            
        Returns:
            Element text or None if not found
        """
        element = self.find_element(selector, by)
        if element:
            try:
                return element.text.strip()
            except Exception as e:
                self.logger.error(f"Error getting text from element {selector}: {e}")
        return None
    
    def get_attribute(
        self,
        selector: str,
        attribute: str,
        by: By = By.CSS_SELECTOR
    ) -> Optional[str]:
        """
        Get attribute value of an element.
        
        Args:
            selector: Element selector
            attribute: Attribute name
            by: Selenium By locator type
            
        Returns:
            Attribute value or None if not found
        """
        element = self.find_element(selector, by)
        if element:
            try:
                return element.get_attribute(attribute)
            except Exception as e:
                self.logger.error(f"Error getting attribute {attribute} from element {selector}: {e}")
        return None
    
    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser.
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script
            
        Returns:
            Script return value
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            self.logger.error(f"Error executing script: {e}")
            return None
    
    def take_screenshot(self, file_path: str) -> bool:
        """
        Take a screenshot of the current page.
        
        Args:
            file_path: Path to save screenshot
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            success = self.driver.save_screenshot(file_path)
            if success:
                self.logger.debug(f"Screenshot saved: {file_path}")
            return success
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return False
    
    def get_page_source(self) -> str:
        """
        Get the current page source.
        
        Returns:
            Page source HTML
        """
        try:
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Error getting page source: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """
        Get the current page URL.
        
        Returns:
            Current URL
        """
        try:
            return self.driver.current_url
        except Exception as e:
            self.logger.error(f"Error getting current URL: {e}")
            return ""
    
    def is_driver_alive(self) -> bool:
        """
        Check if the WebDriver is still alive and responsive.
        
        Returns:
            True if driver is alive, False otherwise
        """
        if self._driver is None:
            return False
        
        try:
            # Try to get current URL as a simple test
            self._driver.current_url
            return True
        except Exception:
            return False