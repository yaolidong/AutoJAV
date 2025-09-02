"""Factory for creating and configuring scrapers."""

import logging
from typing import List, Optional, Dict, Any

from .base_scraper import BaseScraper
from .javdb_scraper import JavDBScraper
from .javlibrary_scraper import JavLibraryScraper
from .javbus_scraper import JAVBusScraper
from .metadata_scraper import MetadataScraper
from .parallel_metadata_scraper import ParallelMetadataScraper
from ..utils.webdriver_manager import WebDriverManager
from ..utils.login_manager import LoginManager
from ..utils.http_client import HttpClient


class ScraperFactory:
    """Factory for creating and configuring scrapers and the metadata coordinator."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the scraper factory.
        
        Args:
            config: Configuration dictionary with scraper settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.default_config = {
            'scrapers': {
                'javdb': {
                    'enabled': True,
                    'use_login': True,
                    'priority': 1
                },
                'javlibrary': {
                    'enabled': True,
                    'use_login': False,
                    'priority': 2,
                    'language': 'en'
                }
            },
            'coordinator': {
                'max_concurrent_requests': 3,
                'timeout_seconds': 60,
                'retry_attempts': 2,
                'cache_duration_minutes': 60
            },
            'webdriver': {
                'headless': True,
                'timeout': 30,
                'user_agent': None
            },
            'http_client': {
                'timeout': 30,
                'max_retries': 3,
                'rate_limit_delay': 2.0
            },
            'login': {
                'javdb_username': None,
                'javdb_password': None
            }
        }
    
    def create_parallel_metadata_scraper(
        self,
        webdriver_manager: Optional[WebDriverManager] = None,
        http_client: Optional[HttpClient] = None
    ) -> ParallelMetadataScraper:
        """
        Create a parallel metadata scraper that queries all sources simultaneously.
        
        Args:
            webdriver_manager: Optional WebDriver manager instance
            http_client: Optional HTTP client instance
            
        Returns:
            Configured ParallelMetadataScraper instance
        """
        scrapers = self._create_scrapers(webdriver_manager, http_client)
        
        coordinator_config = self.config.get('coordinator', {})
        
        parallel_scraper = ParallelMetadataScraper(
            scrapers=scrapers,
            cache_duration_minutes=coordinator_config.get('cache_duration_minutes', 60),
            parallel_timeout=coordinator_config.get('parallel_timeout', 30)
        )
        
        self.logger.info(f"Created ParallelMetadataScraper with {len(scrapers)} scrapers")
        return parallel_scraper
    
    def create_metadata_scraper(
        self,
        webdriver_manager: Optional[WebDriverManager] = None,
        http_client: Optional[HttpClient] = None
    ) -> MetadataScraper:
        """
        Create a configured MetadataScraper with all available scrapers.
        
        Args:
            webdriver_manager: Optional WebDriver manager instance
            http_client: Optional HTTP client instance
            
        Returns:
            Configured MetadataScraper instance
        """
        self.logger.info("Creating MetadataScraper with configured scrapers")
        
        # Create scrapers based on configuration
        scrapers = self._create_scrapers(webdriver_manager, http_client)
        
        if not scrapers:
            raise ValueError("No scrapers could be created. Check configuration.")
        
        # Get coordinator configuration
        coordinator_config = self._get_coordinator_config()
        
        # Create and return MetadataScraper
        metadata_scraper = MetadataScraper(
            scrapers=scrapers,
            **coordinator_config
        )
        
        self.logger.info(f"Created MetadataScraper with {len(scrapers)} scrapers")
        return metadata_scraper
    
    def _create_scrapers(
        self,
        webdriver_manager: Optional[WebDriverManager] = None,
        http_client: Optional[HttpClient] = None
    ) -> List[BaseScraper]:
        """
        Create individual scraper instances based on configuration.
        
        Args:
            webdriver_manager: Optional WebDriver manager instance
            http_client: Optional HTTP client instance
            
        Returns:
            List of configured scraper instances
        """
        scrapers = []
        scraper_configs = self._get_scraper_configs()
        
        # Sort scrapers by priority
        sorted_scrapers = sorted(
            scraper_configs.items(),
            key=lambda x: x[1].get('priority', 999)
        )
        
        for scraper_name, scraper_config in sorted_scrapers:
            if not scraper_config.get('enabled', True):
                self.logger.debug(f"Skipping disabled scraper: {scraper_name}")
                continue
            
            try:
                scraper = self._create_scraper(
                    scraper_name,
                    scraper_config,
                    webdriver_manager,
                    http_client
                )
                
                if scraper:
                    scrapers.append(scraper)
                    self.logger.info(f"Created scraper: {scraper_name}")
                else:
                    self.logger.warning(f"Failed to create scraper: {scraper_name}")
                    
            except Exception as e:
                self.logger.error(f"Error creating scraper {scraper_name}: {e}")
                continue
        
        return scrapers
    
    def _create_scraper(
        self,
        scraper_name: str,
        scraper_config: Dict[str, Any],
        webdriver_manager: Optional[WebDriverManager] = None,
        http_client: Optional[HttpClient] = None
    ) -> Optional[BaseScraper]:
        """
        Create a specific scraper instance.
        
        Args:
            scraper_name: Name of the scraper to create
            scraper_config: Configuration for the scraper
            webdriver_manager: Optional WebDriver manager instance
            http_client: Optional HTTP client instance
            
        Returns:
            Configured scraper instance or None if creation failed
        """
        if scraper_name == 'javdb':
            return self._create_javdb_scraper(scraper_config, webdriver_manager)
        elif scraper_name == 'javlibrary':
            return self._create_javlibrary_scraper(scraper_config, http_client)
        elif scraper_name == 'javbus':
            return self._create_javbus_scraper(scraper_config, http_client)
        else:
            self.logger.warning(f"Unknown scraper type: {scraper_name}")
            return None
    
    def _create_javdb_scraper(
        self,
        scraper_config: Dict[str, Any],
        webdriver_manager: Optional[WebDriverManager] = None
    ) -> Optional[JavDBScraper]:
        """
        Create JavDB scraper instance.
        
        Args:
            scraper_config: JavDB scraper configuration
            webdriver_manager: WebDriver manager instance
            
        Returns:
            Configured JavDBScraper instance or None
        """
        try:
            # Create WebDriver manager if not provided
            if webdriver_manager is None:
                webdriver_config = self._get_webdriver_config()
                webdriver_manager = WebDriverManager(**webdriver_config)
                # Start the WebDriver
                webdriver_manager.start_driver()
            
            # Create login manager if login is enabled
            login_manager = None
            if scraper_config.get('use_login', True):
                login_manager = self._create_login_manager(webdriver_manager)
            
            # Get config directory from configuration
            config_dir = self.config.get('directories', {}).get('config', '/app/config')
            
            # Create JavDB scraper with config_dir for cookie support
            javdb_scraper = JavDBScraper(
                driver_manager=webdriver_manager,
                login_manager=login_manager,
                use_login=scraper_config.get('use_login', True),
                config_dir=config_dir
            )
            
            return javdb_scraper
            
        except Exception as e:
            self.logger.error(f"Failed to create JavDB scraper: {e}")
            return None
    
    def _create_javlibrary_scraper(
        self,
        scraper_config: Dict[str, Any],
        http_client: Optional[HttpClient] = None
    ) -> Optional[JavLibraryScraper]:
        """
        Create JavLibrary scraper instance.
        
        Args:
            scraper_config: JavLibrary scraper configuration
            http_client: HTTP client instance
            
        Returns:
            Configured JavLibraryScraper instance or None
        """
        try:
            # Create HTTP client if not provided
            if http_client is None:
                http_config = self._get_http_client_config()
                http_client = HttpClient(**http_config)
            
            # Create JavLibrary scraper
            javlibrary_scraper = JavLibraryScraper(
                http_client=http_client,
                language=scraper_config.get('language', 'en')
            )
            
            return javlibrary_scraper
            
        except Exception as e:
            self.logger.error(f"Failed to create JavLibrary scraper: {e}")
            return None
    
    def _create_javbus_scraper(
        self,
        scraper_config: Dict[str, Any],
        http_client: Optional[HttpClient] = None
    ) -> Optional[JAVBusScraper]:
        """
        Create JAVBus scraper instance.
        
        Args:
            scraper_config: JAVBus scraper configuration
            http_client: HTTP client instance
            
        Returns:
            Configured JAVBusScraper instance or None
        """
        try:
            # Create HTTP client if not provided
            if http_client is None:
                http_config = self._get_http_client_config()
                http_client = HttpClient(**http_config)
            
            # Create JAVBus scraper
            javbus_scraper = JAVBusScraper(http_client=http_client)
            
            self.logger.debug("Created JAVBus scraper instance")
            return javbus_scraper
            
        except Exception as e:
            self.logger.error(f"Failed to create JAVBus scraper: {e}")
            return None
    
    def _create_login_manager(self, webdriver_manager: WebDriverManager) -> Optional[LoginManager]:
        """
        Create login manager for scrapers that require authentication.
        
        Args:
            webdriver_manager: WebDriver manager instance
            
        Returns:
            Configured LoginManager instance or None
        """
        try:
            login_config = self._get_login_config()
            
            username = login_config.get('javdb_username')
            password = login_config.get('javdb_password')
            
            if not username or not password:
                self.logger.warning("JavDB login credentials not provided")
                return None
            
            login_manager = LoginManager(
                username=username,
                password=password,
                driver_manager=webdriver_manager
            )
            
            return login_manager
            
        except Exception as e:
            self.logger.error(f"Failed to create login manager: {e}")
            return None
    
    def _get_scraper_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get scraper configurations.
        
        Returns:
            Dictionary of scraper configurations
        """
        default_scrapers = self.default_config['scrapers']
        config_scrapers = self.config.get('scrapers', {})
        
        # Merge configurations
        merged_configs = {}
        for scraper_name in default_scrapers:
            merged_configs[scraper_name] = {
                **default_scrapers[scraper_name],
                **config_scrapers.get(scraper_name, {})
            }
        
        return merged_configs
    
    def _get_coordinator_config(self) -> Dict[str, Any]:
        """
        Get coordinator configuration.
        
        Returns:
            Dictionary of coordinator configuration
        """
        default_coordinator = self.default_config['coordinator']
        config_coordinator = self.config.get('coordinator', {})
        
        return {
            **default_coordinator,
            **config_coordinator
        }
    
    def _get_webdriver_config(self) -> Dict[str, Any]:
        """
        Get WebDriver configuration.
        
        Returns:
            Dictionary of WebDriver configuration
        """
        default_webdriver = self.default_config['webdriver']
        config_webdriver = self.config.get('webdriver', {})
        
        return {
            **default_webdriver,
            **config_webdriver
        }
    
    def _get_http_client_config(self) -> Dict[str, Any]:
        """
        Get HTTP client configuration.
        
        Returns:
            Dictionary of HTTP client configuration
        """
        default_http = self.default_config['http_client']
        config_http = self.config.get('http_client', {})
        
        return {
            **default_http,
            **config_http
        }
    
    def _get_login_config(self) -> Dict[str, Any]:
        """
        Get login configuration.
        
        Returns:
            Dictionary of login configuration
        """
        default_login = self.default_config['login']
        config_login = self.config.get('login', {})
        
        return {
            **default_login,
            **config_login
        }
    
    def get_scraper(self, scraper_name: str) -> Optional[BaseScraper]:
        """
        Get a single scraper instance by name.
        
        Args:
            scraper_name: Name of the scraper ('javdb', 'javlibrary', 'javbus')
            
        Returns:
            Configured scraper instance or None if not found
        """
        scraper_configs = self._get_scraper_configs()
        
        if scraper_name not in scraper_configs:
            self.logger.error(f"Unknown scraper: {scraper_name}")
            return None
            
        scraper_config = scraper_configs[scraper_name]
        
        if not scraper_config.get('enabled', True):
            self.logger.warning(f"Scraper {scraper_name} is disabled")
            return None
        
        return self._create_scraper(scraper_name, scraper_config)
    
    def get_available_scrapers(self) -> List[str]:
        """
        Get list of available scraper names.
        
        Returns:
            List of available scraper names
        """
        scraper_configs = self._get_scraper_configs()
        return [
            name for name, config in scraper_configs.items()
            if config.get('enabled', True)
        ]
    
    def validate_config(self) -> Dict[str, List[str]]:
        """
        Validate the current configuration.
        
        Returns:
            Dictionary with validation results (errors and warnings)
        """
        errors = []
        warnings = []
        
        # Check scraper configurations
        scraper_configs = self._get_scraper_configs()
        
        enabled_scrapers = [
            name for name, config in scraper_configs.items()
            if config.get('enabled', True)
        ]
        
        if not enabled_scrapers:
            errors.append("No scrapers are enabled")
        
        # Check JavDB login configuration if enabled
        javdb_config = scraper_configs.get('javdb', {})
        if javdb_config.get('enabled', True) and javdb_config.get('use_login', True):
            login_config = self._get_login_config()
            if not login_config.get('javdb_username'):
                warnings.append("JavDB username not configured")
            if not login_config.get('javdb_password'):
                warnings.append("JavDB password not configured")
        
        # Check coordinator configuration
        coordinator_config = self._get_coordinator_config()
        
        if coordinator_config.get('max_concurrent_requests', 0) <= 0:
            errors.append("max_concurrent_requests must be positive")
        
        if coordinator_config.get('timeout_seconds', 0) <= 0:
            errors.append("timeout_seconds must be positive")
        
        if coordinator_config.get('retry_attempts', 0) < 0:
            errors.append("retry_attempts cannot be negative")
        
        return {
            'errors': errors,
            'warnings': warnings
        }
    
    def create_default_config(self) -> Dict[str, Any]:
        """
        Create a default configuration dictionary.
        
        Returns:
            Default configuration dictionary
        """
        return self.default_config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update the factory configuration.
        
        Args:
            new_config: New configuration to merge
        """
        self.config.update(new_config)
        self.logger.info("Updated scraper factory configuration")