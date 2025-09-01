"""Tests for ScraperFactory."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.scrapers.scraper_factory import ScraperFactory
from src.scrapers.metadata_scraper import MetadataScraper
from src.scrapers.javdb_scraper import JavDBScraper
from src.scrapers.javlibrary_scraper import JavLibraryScraper
from src.utils.webdriver_manager import WebDriverManager
from src.utils.login_manager import LoginManager
from src.utils.http_client import HttpClient


class TestScraperFactory:
    """Test cases for ScraperFactory."""
    
    @pytest.fixture
    def factory(self):
        """Create ScraperFactory instance."""
        return ScraperFactory()
    
    @pytest.fixture
    def factory_with_config(self):
        """Create ScraperFactory with custom configuration."""
        config = {
            'scrapers': {
                'javdb': {
                    'enabled': True,
                    'use_login': False,
                    'priority': 2
                },
                'javlibrary': {
                    'enabled': False,
                    'priority': 1
                }
            },
            'coordinator': {
                'max_concurrent_requests': 5,
                'timeout_seconds': 30
            },
            'login': {
                'javdb_username': 'test_user',
                'javdb_password': 'test_pass'
            }
        }
        return ScraperFactory(config)
    
    def test_init_default(self, factory):
        """Test factory initialization with default configuration."""
        assert factory.config == {}
        assert 'scrapers' in factory.default_config
        assert 'coordinator' in factory.default_config
        assert 'webdriver' in factory.default_config
        assert 'http_client' in factory.default_config
        assert 'login' in factory.default_config
    
    def test_init_with_config(self, factory_with_config):
        """Test factory initialization with custom configuration."""
        assert factory_with_config.config['scrapers']['javdb']['enabled'] is True
        assert factory_with_config.config['scrapers']['javlibrary']['enabled'] is False
    
    def test_get_scraper_configs_default(self, factory):
        """Test getting scraper configurations with defaults."""
        configs = factory._get_scraper_configs()
        
        assert 'javdb' in configs
        assert 'javlibrary' in configs
        assert configs['javdb']['enabled'] is True
        assert configs['javdb']['use_login'] is True
        assert configs['javdb']['priority'] == 1
        assert configs['javlibrary']['enabled'] is True
        assert configs['javlibrary']['priority'] == 2
    
    def test_get_scraper_configs_merged(self, factory_with_config):
        """Test getting scraper configurations with custom overrides."""
        configs = factory_with_config._get_scraper_configs()
        
        assert configs['javdb']['enabled'] is True
        assert configs['javdb']['use_login'] is False  # Overridden
        assert configs['javdb']['priority'] == 2  # Overridden
        assert configs['javlibrary']['enabled'] is False  # Overridden
    
    def test_get_coordinator_config_default(self, factory):
        """Test getting coordinator configuration with defaults."""
        config = factory._get_coordinator_config()
        
        assert config['max_concurrent_requests'] == 3
        assert config['timeout_seconds'] == 60
        assert config['retry_attempts'] == 2
        assert config['cache_duration_minutes'] == 60
    
    def test_get_coordinator_config_custom(self, factory_with_config):
        """Test getting coordinator configuration with custom values."""
        config = factory_with_config._get_coordinator_config()
        
        assert config['max_concurrent_requests'] == 5  # Overridden
        assert config['timeout_seconds'] == 30  # Overridden
        assert config['retry_attempts'] == 2  # Default
    
    def test_get_webdriver_config(self, factory):
        """Test getting WebDriver configuration."""
        config = factory._get_webdriver_config()
        
        assert 'headless' in config
        assert 'timeout' in config
        assert 'user_agent' in config
        assert config['headless'] is True
        assert config['timeout'] == 30
    
    def test_get_http_client_config(self, factory):
        """Test getting HTTP client configuration."""
        config = factory._get_http_client_config()
        
        assert 'timeout' in config
        assert 'max_retries' in config
        assert 'rate_limit_delay' in config
        assert config['timeout'] == 30
        assert config['max_retries'] == 3
    
    def test_get_login_config_default(self, factory):
        """Test getting login configuration with defaults."""
        config = factory._get_login_config()
        
        assert config['javdb_username'] is None
        assert config['javdb_password'] is None
    
    def test_get_login_config_custom(self, factory_with_config):
        """Test getting login configuration with custom values."""
        config = factory_with_config._get_login_config()
        
        assert config['javdb_username'] == 'test_user'
        assert config['javdb_password'] == 'test_pass'
    
    def test_get_available_scrapers_default(self, factory):
        """Test getting available scrapers with default configuration."""
        scrapers = factory.get_available_scrapers()
        
        assert 'javdb' in scrapers
        assert 'javlibrary' in scrapers
        assert len(scrapers) == 2
    
    def test_get_available_scrapers_filtered(self, factory_with_config):
        """Test getting available scrapers with some disabled."""
        scrapers = factory_with_config.get_available_scrapers()
        
        assert 'javdb' in scrapers
        assert 'javlibrary' not in scrapers  # Disabled
        assert len(scrapers) == 1
    
    @patch('src.scrapers.scraper_factory.JavDBScraper')
    @patch('src.scrapers.scraper_factory.JavLibraryScraper')
    @patch('src.scrapers.scraper_factory.WebDriverManager')
    @patch('src.scrapers.scraper_factory.HttpClient')
    def test_create_scrapers_success(self, mock_http_client, mock_webdriver, mock_javlib, mock_javdb, factory):
        """Test successful creation of scrapers."""
        # Mock the scraper classes
        mock_javdb_instance = Mock()
        mock_javlib_instance = Mock()
        mock_javdb.return_value = mock_javdb_instance
        mock_javlib.return_value = mock_javlib_instance
        
        scrapers = factory._create_scrapers()
        
        assert len(scrapers) == 2
        assert mock_javdb_instance in scrapers
        assert mock_javlib_instance in scrapers
    
    @patch('src.scrapers.scraper_factory.JavDBScraper')
    @patch('src.scrapers.scraper_factory.WebDriverManager')
    def test_create_javdb_scraper_success(self, mock_webdriver, mock_javdb, factory):
        """Test successful creation of JavDB scraper."""
        mock_webdriver_instance = Mock()
        mock_webdriver.return_value = mock_webdriver_instance
        mock_javdb_instance = Mock()
        mock_javdb.return_value = mock_javdb_instance
        
        scraper_config = {'use_login': True}
        
        result = factory._create_javdb_scraper(scraper_config)
        
        assert result == mock_javdb_instance
        mock_javdb.assert_called_once()
    
    @patch('src.scrapers.scraper_factory.JavDBScraper')
    def test_create_javdb_scraper_with_provided_webdriver(self, mock_javdb, factory):
        """Test creation of JavDB scraper with provided WebDriver manager."""
        mock_webdriver_manager = Mock()
        mock_javdb_instance = Mock()
        mock_javdb.return_value = mock_javdb_instance
        
        scraper_config = {'use_login': False}
        
        result = factory._create_javdb_scraper(scraper_config, mock_webdriver_manager)
        
        assert result == mock_javdb_instance
        mock_javdb.assert_called_once_with(
            driver_manager=mock_webdriver_manager,
            login_manager=None,
            use_login=False
        )
    
    @patch('src.scrapers.scraper_factory.JavLibraryScraper')
    @patch('src.scrapers.scraper_factory.HttpClient')
    def test_create_javlibrary_scraper_success(self, mock_http_client, mock_javlib, factory):
        """Test successful creation of JavLibrary scraper."""
        mock_http_instance = Mock()
        mock_http_client.return_value = mock_http_instance
        mock_javlib_instance = Mock()
        mock_javlib.return_value = mock_javlib_instance
        
        scraper_config = {'language': 'ja'}
        
        result = factory._create_javlibrary_scraper(scraper_config)
        
        assert result == mock_javlib_instance
        mock_javlib.assert_called_once_with(
            http_client=mock_http_instance,
            language='ja'
        )
    
    @patch('src.scrapers.scraper_factory.JavLibraryScraper')
    def test_create_javlibrary_scraper_with_provided_http_client(self, mock_javlib, factory):
        """Test creation of JavLibrary scraper with provided HTTP client."""
        mock_http_client = Mock()
        mock_javlib_instance = Mock()
        mock_javlib.return_value = mock_javlib_instance
        
        scraper_config = {'language': 'en'}
        
        result = factory._create_javlibrary_scraper(scraper_config, mock_http_client)
        
        assert result == mock_javlib_instance
        mock_javlib.assert_called_once_with(
            http_client=mock_http_client,
            language='en'
        )
    
    @patch('src.scrapers.scraper_factory.LoginManager')
    def test_create_login_manager_success(self, mock_login_manager, factory_with_config):
        """Test successful creation of login manager."""
        mock_webdriver_manager = Mock()
        mock_login_instance = Mock()
        mock_login_manager.return_value = mock_login_instance
        
        result = factory_with_config._create_login_manager(mock_webdriver_manager)
        
        assert result == mock_login_instance
        mock_login_manager.assert_called_once_with(
            username='test_user',
            password='test_pass',
            driver_manager=mock_webdriver_manager
        )
    
    def test_create_login_manager_no_credentials(self, factory):
        """Test login manager creation without credentials."""
        mock_webdriver_manager = Mock()
        
        result = factory._create_login_manager(mock_webdriver_manager)
        
        assert result is None
    
    def test_create_scraper_unknown_type(self, factory):
        """Test creation of unknown scraper type."""
        result = factory._create_scraper('unknown', {}, None, None)
        
        assert result is None
    
    @patch('src.scrapers.scraper_factory.MetadataScraper')
    def test_create_metadata_scraper_success(self, mock_metadata_scraper, factory):
        """Test successful creation of MetadataScraper."""
        mock_scraper_instance = Mock()
        mock_metadata_scraper.return_value = mock_scraper_instance
        
        with patch.object(factory, '_create_scrapers') as mock_create_scrapers:
            mock_scrapers = [Mock(), Mock()]
            mock_create_scrapers.return_value = mock_scrapers
            
            result = factory.create_metadata_scraper()
            
            assert result == mock_scraper_instance
            mock_metadata_scraper.assert_called_once()
            
            # Check that coordinator config was passed
            call_args = mock_metadata_scraper.call_args
            assert 'scrapers' in call_args.kwargs
            assert call_args.kwargs['scrapers'] == mock_scrapers
    
    def test_create_metadata_scraper_no_scrapers(self, factory):
        """Test MetadataScraper creation when no scrapers available."""
        with patch.object(factory, '_create_scrapers') as mock_create_scrapers:
            mock_create_scrapers.return_value = []
            
            with pytest.raises(ValueError, match="No scrapers could be created"):
                factory.create_metadata_scraper()
    
    def test_validate_config_valid(self, factory_with_config):
        """Test configuration validation with valid config."""
        result = factory_with_config.validate_config()
        
        assert isinstance(result, dict)
        assert 'errors' in result
        assert 'warnings' in result
        assert len(result['errors']) == 0
    
    def test_validate_config_no_enabled_scrapers(self):
        """Test configuration validation with no enabled scrapers."""
        config = {
            'scrapers': {
                'javdb': {'enabled': False},
                'javlibrary': {'enabled': False}
            }
        }
        factory = ScraperFactory(config)
        
        result = factory.validate_config()
        
        assert 'No scrapers are enabled' in result['errors']
    
    def test_validate_config_missing_login_credentials(self, factory):
        """Test configuration validation with missing login credentials."""
        result = factory.validate_config()
        
        # Should have warnings about missing credentials
        warnings = result['warnings']
        assert any('username' in warning for warning in warnings)
        assert any('password' in warning for warning in warnings)
    
    def test_validate_config_invalid_coordinator_settings(self):
        """Test configuration validation with invalid coordinator settings."""
        config = {
            'coordinator': {
                'max_concurrent_requests': 0,
                'timeout_seconds': -1,
                'retry_attempts': -1
            }
        }
        factory = ScraperFactory(config)
        
        result = factory.validate_config()
        
        errors = result['errors']
        assert any('max_concurrent_requests must be positive' in error for error in errors)
        assert any('timeout_seconds must be positive' in error for error in errors)
        assert any('retry_attempts cannot be negative' in error for error in errors)
    
    def test_create_default_config(self, factory):
        """Test creation of default configuration."""
        config = factory.create_default_config()
        
        assert isinstance(config, dict)
        assert 'scrapers' in config
        assert 'coordinator' in config
        assert 'webdriver' in config
        assert 'http_client' in config
        assert 'login' in config
        
        # Should be a copy, not the same object
        assert config is not factory.default_config
    
    def test_update_config(self, factory):
        """Test updating factory configuration."""
        new_config = {
            'scrapers': {
                'javdb': {'enabled': False}
            },
            'new_setting': 'test_value'
        }
        
        factory.update_config(new_config)
        
        assert factory.config['scrapers']['javdb']['enabled'] is False
        assert factory.config['new_setting'] == 'test_value'
    
    @patch('src.scrapers.scraper_factory.JavDBScraper')
    def test_create_javdb_scraper_exception(self, mock_javdb, factory):
        """Test JavDB scraper creation with exception."""
        mock_javdb.side_effect = Exception("Creation failed")
        
        result = factory._create_javdb_scraper({})
        
        assert result is None
    
    @patch('src.scrapers.scraper_factory.JavLibraryScraper')
    def test_create_javlibrary_scraper_exception(self, mock_javlib, factory):
        """Test JavLibrary scraper creation with exception."""
        mock_javlib.side_effect = Exception("Creation failed")
        
        result = factory._create_javlibrary_scraper({})
        
        assert result is None
    
    @patch('src.scrapers.scraper_factory.LoginManager')
    def test_create_login_manager_exception(self, mock_login_manager, factory_with_config):
        """Test login manager creation with exception."""
        mock_login_manager.side_effect = Exception("Login manager creation failed")
        mock_webdriver_manager = Mock()
        
        result = factory_with_config._create_login_manager(mock_webdriver_manager)
        
        assert result is None
    
    def test_scraper_priority_ordering(self, factory):
        """Test that scrapers are created in priority order."""
        config = {
            'scrapers': {
                'javdb': {'priority': 3, 'enabled': True},
                'javlibrary': {'priority': 1, 'enabled': True}
            }
        }
        factory = ScraperFactory(config)
        
        with patch.object(factory, '_create_scraper') as mock_create_scraper:
            mock_create_scraper.return_value = Mock()
            
            factory._create_scrapers()
            
            # Should be called in priority order (javlibrary first, then javdb)
            calls = mock_create_scraper.call_args_list
            assert calls[0][0][0] == 'javlibrary'  # First call should be javlibrary
            assert calls[1][0][0] == 'javdb'  # Second call should be javdb


if __name__ == "__main__":
    pytest.main([__file__])