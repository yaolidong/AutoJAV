"""Configuration manager for loading and validating settings."""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from ..models.config import Config


class ConfigManager:
    """Manages application configuration from files and environment variables."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to the configuration file. If None, uses default locations.
        """
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or self._find_config_file()
        self._config_data: Optional[Dict[str, Any]] = None
        self._config: Optional[Config] = None
    
    def _find_config_file(self) -> str:
        """Find the configuration file in default locations."""
        possible_paths = [
            os.getenv('CONFIG_FILE'),
            'config/config.yaml',
            'config/config.yml',
            '/app/config/config.yaml',
            os.path.expanduser('~/.av-scraper/config.yaml')
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                self.logger.info(f"Found config file: {path}")
                return path
        
        # Return default path even if it doesn't exist
        return 'config/config.yaml'
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file and environment variables.
        
        Returns:
            Dictionary containing all configuration data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        if self._config_data is not None:
            return self._config_data
        
        # Try app_config.yaml first
        app_config_path = Path(self.config_file).parent / 'app_config.yaml'
        config_path = Path(self.config_file)
        
        if app_config_path.exists():
            try:
                with open(app_config_path, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f) or {}
                self.logger.info(f"Loaded config from: {app_config_path}")
            except yaml.YAMLError as e:
                self.logger.error(f"Invalid YAML in app config file: {e}")
                self._config_data = self._get_default_config()
            except Exception as e:
                self.logger.error(f"Error reading app config file: {e}")
                self._config_data = self._get_default_config()
        elif not config_path.exists():
            self.logger.warning(f"Config file not found: {config_path}")
            self._config_data = self._get_default_config()
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if it's TOML format (Selenium Grid config)
                if content.strip().startswith('['):
                    self.logger.info("Detected TOML format config (Selenium Grid), using default app config")
                    self._config_data = self._get_default_config()
                else:
                    # Parse as YAML
                    self._config_data = yaml.safe_load(content) or {}
                    self.logger.info(f"Loaded config from: {config_path}")
            except yaml.YAMLError as e:
                self.logger.error(f"Invalid YAML in config file: {e}")
                self._config_data = self._get_default_config()
            except Exception as e:
                self.logger.error(f"Error reading config file: {e}")
                self._config_data = self._get_default_config()
        
        # Override with environment variables
        self._apply_env_overrides()

        if isinstance(self._config_data, dict):
            self._merge_defaults(self._config_data, self._get_default_config())
        
        return self._config_data
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'directories': {
                'source': os.getenv('SOURCE_DIR', '/app/source'),
                'target': os.getenv('TARGET_DIR', '/app/target')
            },
            'credentials': {
                'javdb': {
                    'username': '',
                    'password': ''
                }
            },
            'scrapers': {
                'javdb': {
                    'base_url': os.getenv('JAVDB_BASE_URL', 'https://javdb.com'),
                    'mirrors': []
                }
            },
            'scraping': {
                'priority': ['javdb', 'javlibrary'],
                'max_concurrent_files': 3,
                'retry_attempts': 3,
                'timeout': 30,
                'success_criteria': {
                    'require_actress': True,
                    'require_title': True,
                    'require_code': True,
                    'images_optional': True
                }
            },
            'organization': {
                'naming_pattern': '{actress}/{code}/{code}.{ext}',
                'conflict_resolution': 'rename',
                'download_images': True,
                'save_metadata': True,
                'safe_mode': False,
                'actor_selection': 'first'
            },
            'browser': {
                'headless': True,
                'timeout': 30
            },
            'network': {
                'proxy_url': ''
            },
            'logging': {
                'level': 'INFO'
            },
            'supported_extensions': ['.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v']
        }

    def _merge_defaults(self, target: Dict[str, Any], defaults: Dict[str, Any]) -> None:
        """Recursively merge default configuration values without overwriting user-defined settings."""
        for key, default_value in defaults.items():
            if key not in target:
                if isinstance(default_value, dict):
                    target[key] = default_value.copy()
                elif isinstance(default_value, list):
                    target[key] = list(default_value)
                else:
                    target[key] = default_value
            else:
                current_value = target[key]
                if isinstance(default_value, dict) and isinstance(current_value, dict):
                    self._merge_defaults(current_value, default_value)
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            'SOURCE_DIR': ['directories', 'source'],
            'TARGET_DIR': ['directories', 'target'],
            'JAVDB_USERNAME': ['credentials', 'javdb', 'username'],
            'JAVDB_PASSWORD': ['credentials', 'javdb', 'password'],
            'MAX_CONCURRENT_FILES': ['scraping', 'max_concurrent_files'],
            'RETRY_ATTEMPTS': ['scraping', 'retry_attempts'],
            'BROWSER_TIMEOUT': ['browser', 'timeout'],
            'PROXY_URL': ['network', 'proxy_url'],
            'LOG_LEVEL': ['logging', 'level'],
            'HEADLESS_BROWSER': ['browser', 'headless'],
            'DOWNLOAD_IMAGES': ['organization', 'download_images'],
            'SAVE_METADATA': ['organization', 'save_metadata'],
            'JAVDB_BASE_URL': ['scrapers', 'javdb', 'base_url']
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if env_var in ['MAX_CONCURRENT_FILES', 'RETRY_ATTEMPTS', 'BROWSER_TIMEOUT']:
                    try:
                        value = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {value}")
                        continue
                elif env_var in ['HEADLESS_BROWSER', 'DOWNLOAD_IMAGES', 'SAVE_METADATA']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                # Set the value in config
                self._set_nested_value(self._config_data, config_path, value)
                self.logger.debug(f"Applied env override: {env_var} = {value}")
    
    def _set_nested_value(self, data: Dict[str, Any], path: List[str], value: Any):
        """Set a nested value in the configuration dictionary."""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-separated key.
        
        Args:
            key: Dot-separated key (e.g., 'directories.source')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if self._config_data is None:
            self.load_config()
        
        keys = key.split('.')
        current = self._config_data
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_config_data(self) -> Dict[str, Any]:
        """
        Get the raw configuration data as a dictionary.
        
        Returns:
            Dictionary with all configuration settings
        """
        if self._config_data is None:
            self.load_config()
        return self._config_data or {}
    
    def get_config(self) -> Config:
        """
        Get the configuration as a Config object.
        
        Returns:
            Config object with all settings
            
        Raises:
            ValueError: If configuration is invalid
        """
        if self._config is not None:
            return self._config
        
        if self._config_data is None:
            self.load_config()
        
        try:
            # Extract values from nested config
            config_dict = {
                'source_directory': self.get('directories.source'),
                'target_directory': self.get('directories.target'),
                'javdb_username': self.get('credentials.javdb.username'),
                'javdb_password': self.get('credentials.javdb.password'),
                'scraper_priority': self.get('scraping.priority', ['javdb', 'javlibrary']),
                'max_concurrent_files': self.get('scraping.max_concurrent_files', 3),
                'retry_attempts': self.get('scraping.retry_attempts', 3),
                'naming_pattern': self.get('organization.naming_pattern', '{actress}/{code}/{code}.{ext}'),
                'headless_browser': self.get('browser.headless', True),
                'browser_timeout': self.get('browser.timeout', 30),
                'proxy_url': self.get('network.proxy_url'),
                'download_images': self.get('organization.download_images', True),
                'save_metadata': self.get('organization.save_metadata', True),
                'log_level': self.get('logging.level', 'INFO'),
                'supported_extensions': self.get('supported_extensions', ['.mp4', '.mkv', '.avi'])
            }
            
            # Remove None values
            config_dict = {k: v for k, v in config_dict.items() if v is not None}
            
            self._config = Config(**config_dict)
            return self._config
            
        except Exception as e:
            self.logger.error(f"Error creating Config object: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    
    def validate_config(self) -> List[str]:
        """
        Validate the configuration and return any errors.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            config = self.get_config()
            
            # Validate directories
            if not config.source_directory:
                errors.append("Source directory is required")
            
            if not config.target_directory:
                errors.append("Target directory is required")
            
            # Add Config model validation errors
            config_errors = config.validate_directories()
            errors.extend(config_errors)
            
            # Validate scraper priority
            valid_scrapers = ['javdb', 'javlibrary']
            for scraper in config.scraper_priority:
                if scraper not in valid_scrapers:
                    errors.append(f"Invalid scraper in priority list: {scraper}")
            
            # Validate naming pattern
            required_placeholders = ['{code}', '{ext}']
            for placeholder in required_placeholders:
                if placeholder not in config.naming_pattern:
                    errors.append(f"Naming pattern must contain {placeholder}")
            
        except Exception as e:
            errors.append(f"Configuration validation failed: {e}")
        
        return errors
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """
        Save current configuration to file.
        
        Args:
            config_path: Path to save config file. If None, uses current config file.
            
        Returns:
            True if saved successfully, False otherwise
        """
        if self._config_data is None:
            self.logger.error("No configuration data to save")
            return False
        
        save_path = Path(config_path or self.config_file)
        
        try:
            # Ensure directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def reload_config(self):
        """Reload configuration from file."""
        self._config_data = None
        self._config = None
        self.load_config()