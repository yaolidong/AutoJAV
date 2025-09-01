"""Tests for WebDriverManager."""

import pytest
from unittest.mock import patch, MagicMock
from selenium.common.exceptions import WebDriverException, TimeoutException

from src.utils.webdriver_manager import WebDriverManager


class TestWebDriverManager:
    """Test cases for WebDriverManager."""
    
    def test_init(self):
        """Test WebDriverManager initialization."""
        manager = WebDriverManager(
            headless=False,
            timeout=60,
            proxy_url="http://proxy.example.com:8080",
            user_agent="Custom User Agent",
            window_size=(1280, 720)
        )
        
        assert manager.headless is False
        assert manager.timeout == 60
        assert manager.proxy_url == "http://proxy.example.com:8080"
        assert manager.user_agent == "Custom User Agent"
        assert manager.window_size == (1280, 720)
    
    def test_get_chrome_options_headless(self):
        """Test Chrome options for headless mode."""
        manager = WebDriverManager(headless=True)
        options = manager._get_chrome_options()
        
        # Check that headless argument is present
        assert '--headless' in options.arguments
        assert '--no-sandbox' in options.arguments
        assert '--disable-dev-shm-usage' in options.arguments
    
    def test_get_chrome_options_with_proxy(self):
        """Test Chrome options with proxy."""
        manager = WebDriverManager(proxy_url="http://proxy.example.com:8080")
        options = manager._get_chrome_options()
        
        assert '--proxy-server=http://proxy.example.com:8080' in options.arguments
    
    def test_get_chrome_options_custom_user_agent(self):
        """Test Chrome options with custom user agent."""
        custom_ua = "Custom User Agent String"
        manager = WebDriverManager(user_agent=custom_ua)
        options = manager._get_chrome_options()
        
        assert f'--user-agent={custom_ua}' in options.arguments
    
    @patch('src.utils.webdriver_manager.webdriver.Chrome')
    @patch('src.utils.webdriver_manager.Service')
    @patch('os.path.exists')
    def test_start_driver_system_chromedriver(self, mock_exists, mock_service, mock_chrome):
        """Test starting driver with system chromedriver."""
        # Mock system chromedriver exists
        mock_exists.return_value = True
        
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        manager = WebDriverManager()
        driver = manager.start_driver()
        
        assert driver == mock_driver
        assert manager._driver == mock_driver
        
        # Check that system chromedriver path was used
        mock_service.assert_called_with('/usr/local/bin/chromedriver')
        
        # Check that timeouts were set
        mock_driver.implicitly_wait.assert_called_with(manager.timeout)
        mock_driver.set_page_load_timeout.assert_called_with(manager.timeout)
    
    @patch('src.utils.webdriver_manager.webdriver.Chrome')
    @patch('src.utils.webdriver_manager.Service')
    @patch('src.utils.webdriver_manager.ChromeDriverManager')
    @patch('os.path.exists')
    def test_start_driver_webdriver_manager(self, mock_exists, mock_cdm, mock_service, mock_chrome):
        """Test starting driver with webdriver-manager."""
        # Mock system chromedriver doesn't exist
        mock_exists.return_value = False
        
        # Mock webdriver-manager
        mock_cdm_instance = MagicMock()
        mock_cdm_instance.install.return_value = '/path/to/chromedriver'
        mock_cdm.return_value = mock_cdm_instance
        
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        manager = WebDriverManager()
        driver = manager.start_driver()
        
        assert driver == mock_driver
        mock_service.assert_called_with('/path/to/chromedriver')
    
    @patch('src.utils.webdriver_manager.webdriver.Chrome')
    def test_start_driver_failure(self, mock_chrome):
        """Test driver start failure."""
        mock_chrome.side_effect = Exception("Chrome not found")
        
        manager = WebDriverManager()
        
        with pytest.raises(WebDriverException):
            manager.start_driver()
    
    def test_start_driver_already_started(self):
        """Test starting driver when already started."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        manager._driver = mock_driver
        
        result = manager.start_driver()
        
        assert result == mock_driver
    
    def test_quit_driver(self):
        """Test quitting driver."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_service = MagicMock()
        
        manager._driver = mock_driver
        manager._service = mock_service
        
        manager.quit_driver()
        
        mock_driver.quit.assert_called_once()
        mock_service.stop.assert_called_once()
        assert manager._driver is None
        assert manager._service is None
    
    def test_quit_driver_with_errors(self):
        """Test quitting driver with errors."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_service = MagicMock()
        
        # Mock errors during quit
        mock_driver.quit.side_effect = Exception("Quit error")
        mock_service.stop.side_effect = Exception("Stop error")
        
        manager._driver = mock_driver
        manager._service = mock_service
        
        # Should not raise exceptions
        manager.quit_driver()
        
        assert manager._driver is None
        assert manager._service is None
    
    def test_driver_property_not_started(self):
        """Test driver property when not started."""
        manager = WebDriverManager()
        
        with pytest.raises(RuntimeError, match="WebDriver not started"):
            _ = manager.driver
    
    def test_driver_property_started(self):
        """Test driver property when started."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        manager._driver = mock_driver
        
        assert manager.driver == mock_driver
    
    def test_context_manager(self):
        """Test WebDriverManager as context manager."""
        with patch.object(WebDriverManager, 'start_driver') as mock_start:
            with patch.object(WebDriverManager, 'quit_driver') as mock_quit:
                mock_driver = MagicMock()
                mock_start.return_value = mock_driver
                
                with WebDriverManager() as manager:
                    assert manager._driver == mock_driver
                
                mock_start.assert_called_once()
                mock_quit.assert_called_once()
    
    def test_get_page_success(self):
        """Test successful page navigation."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        manager._driver = mock_driver
        
        result = manager.get_page("http://example.com")
        
        assert result is True
        mock_driver.get.assert_called_with("http://example.com")
    
    def test_get_page_with_wait_element(self):
        """Test page navigation with element wait."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        manager._driver = mock_driver
        
        with patch.object(manager, 'wait_for_element') as mock_wait:
            mock_wait.return_value = MagicMock()  # Element found
            
            result = manager.get_page("http://example.com", wait_for_element=".content")
            
            assert result is True
            mock_wait.assert_called_with(".content")
    
    def test_get_page_failure(self):
        """Test page navigation failure."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("Navigation failed")
        manager._driver = mock_driver
        
        result = manager.get_page("http://example.com")
        
        assert result is False
    
    @patch('src.utils.webdriver_manager.WebDriverWait')
    def test_wait_for_element_success(self, mock_wait_class):
        """Test successful element wait."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        manager._driver = mock_driver
        
        mock_element = MagicMock()
        mock_wait = MagicMock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = manager.wait_for_element(".test-element")
        
        assert result == mock_element
        mock_wait_class.assert_called_with(mock_driver, manager.timeout)
    
    @patch('src.utils.webdriver_manager.WebDriverWait')
    def test_wait_for_element_timeout(self, mock_wait_class):
        """Test element wait timeout."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        manager._driver = mock_driver
        
        mock_wait = MagicMock()
        mock_wait.until.side_effect = TimeoutException("Timeout")
        mock_wait_class.return_value = mock_wait
        
        result = manager.wait_for_element(".test-element")
        
        assert result is None
    
    def test_find_element_success(self):
        """Test successful element finding."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        manager._driver = mock_driver
        
        result = manager.find_element(".test-element")
        
        assert result == mock_element
    
    def test_find_element_not_found(self):
        """Test element not found."""
        from selenium.common.exceptions import NoSuchElementException
        
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        manager._driver = mock_driver
        
        result = manager.find_element(".test-element")
        
        assert result is None
    
    def test_click_element_success(self):
        """Test successful element click."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        manager._driver = mock_driver
        
        result = manager.click_element(".test-button")
        
        assert result is True
        mock_element.click.assert_called_once()
    
    def test_click_element_not_found(self):
        """Test click on non-existent element."""
        from selenium.common.exceptions import NoSuchElementException
        
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("Not found")
        manager._driver = mock_driver
        
        result = manager.click_element(".test-button")
        
        assert result is False
    
    def test_send_keys_success(self):
        """Test successful key sending."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        manager._driver = mock_driver
        
        result = manager.send_keys(".test-input", "test text")
        
        assert result is True
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_with("test text")
    
    def test_get_text_success(self):
        """Test successful text retrieval."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "  Test Text  "
        mock_driver.find_element.return_value = mock_element
        manager._driver = mock_driver
        
        result = manager.get_text(".test-element")
        
        assert result == "Test Text"  # Should be stripped
    
    def test_get_attribute_success(self):
        """Test successful attribute retrieval."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "test-value"
        mock_driver.find_element.return_value = mock_element
        manager._driver = mock_driver
        
        result = manager.get_attribute(".test-element", "data-value")
        
        assert result == "test-value"
        mock_element.get_attribute.assert_called_with("data-value")
    
    def test_execute_script_success(self):
        """Test successful script execution."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = "script result"
        manager._driver = mock_driver
        
        result = manager.execute_script("return document.title;")
        
        assert result == "script result"
        mock_driver.execute_script.assert_called_with("return document.title;")
    
    @patch('pathlib.Path.mkdir')
    def test_take_screenshot_success(self, mock_mkdir):
        """Test successful screenshot."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.save_screenshot.return_value = True
        manager._driver = mock_driver
        
        result = manager.take_screenshot("/tmp/screenshot.png")
        
        assert result is True
        mock_driver.save_screenshot.assert_called_with("/tmp/screenshot.png")
        mock_mkdir.assert_called_once()
    
    def test_get_page_source(self):
        """Test page source retrieval."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Test</body></html>"
        manager._driver = mock_driver
        
        result = manager.get_page_source()
        
        assert result == "<html><body>Test</body></html>"
    
    def test_get_current_url(self):
        """Test current URL retrieval."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.current_url = "http://example.com/current"
        manager._driver = mock_driver
        
        result = manager.get_current_url()
        
        assert result == "http://example.com/current"
    
    def test_is_driver_alive_true(self):
        """Test driver alive check when alive."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.current_url = "http://example.com"
        manager._driver = mock_driver
        
        result = manager.is_driver_alive()
        
        assert result is True
    
    def test_is_driver_alive_false_no_driver(self):
        """Test driver alive check when no driver."""
        manager = WebDriverManager()
        
        result = manager.is_driver_alive()
        
        assert result is False
    
    def test_is_driver_alive_false_exception(self):
        """Test driver alive check when driver throws exception."""
        manager = WebDriverManager()
        mock_driver = MagicMock()
        mock_driver.current_url = Exception("Driver dead")
        manager._driver = mock_driver
        
        result = manager.is_driver_alive()
        
        assert result is False