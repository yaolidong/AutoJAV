"""Tests for ConfigManager."""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config.config_manager import ConfigManager
from src.models.config import Config


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_init_with_config_file(self):
        """Test ConfigManager initialization with config file."""
        manager = ConfigManager("test_config.yaml")
        assert manager.config_file == "test_config.yaml"
    
    def test_init_without_config_file(self):
        """Test ConfigManager initialization without config file."""
        with patch.object(ConfigManager, '_find_config_file', return_value='default.yaml'):
            manager = ConfigManager()
            assert manager.config_file == 'default.yaml'
    
    def test_find_config_file_with_env(self):
        """Test finding config file from environment variable."""
        with patch.dict(os.environ, {'CONFIG_FILE': '/test/config.yaml'}):
            with patch('pathlib.Path.exists', return_value=True):
                manager = ConfigManager()
                assert manager.config_file == '/test/config.yaml'
    
    def test_find_config_file_default_locations(self):
        """Test finding config file in default locations."""
        with patch('pathlib.Path.exists') as mock_exists:
            # First call (env var) returns False, second call (config/config.yaml) returns True
            mock_exists.side_effect = [False, True]
            manager = ConfigManager()
            assert manager.config_file == 'config/config.yaml'
    
    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            'directories': {
                'source': '/test/source',
                'target': '/test/target'
            },
            'logging': {
                'level': 'DEBUG'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            loaded_config = manager.load_config()
            
            assert loaded_config['directories']['source'] == '/test/source'
            assert loaded_config['directories']['target'] == '/test/target'
            assert loaded_config['logging']['level'] == 'DEBUG'
        finally:
            os.unlink(temp_path)
    
    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        manager = ConfigManager('nonexistent.yaml')
        config = manager.load_config()
        
        # Should return default config
        assert 'directories' in config
        assert 'scraping' in config
        assert config['directories']['source'] == '/app/source'
    
    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(yaml.YAMLError):
                manager.load_config()
        finally:
            os.unlink(temp_path)
    
    def test_env_overrides(self):
        """Test environment variable overrides."""
        env_vars = {
            'SOURCE_DIR': '/env/source',
            'TARGET_DIR': '/env/target',
            'MAX_CONCURRENT_FILES': '5',
            'HEADLESS_BROWSER': 'false',
            'LOG_LEVEL': 'ERROR'
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigManager('nonexistent.yaml')  # Will use defaults
            config = manager.load_config()
            
            assert config['directories']['source'] == '/env/source'
            assert config['directories']['target'] == '/env/target'
            assert config['scraping']['max_concurrent_files'] == 5
            assert config['browser']['headless'] is False
            assert config['logging']['level'] == 'ERROR'
    
    def test_get_method(self):
        """Test getting configuration values by key."""
        config_data = {
            'directories': {
                'source': '/test/source'
            },
            'scraping': {
                'max_concurrent_files': 3
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            
            assert manager.get('directories.source') == '/test/source'
            assert manager.get('scraping.max_concurrent_files') == 3
            assert manager.get('nonexistent.key', 'default') == 'default'
            assert manager.get('nonexistent.key') is None
        finally:
            os.unlink(temp_path)
    
    def test_get_config_object(self):
        """Test getting Config object."""
        config_data = {
            'directories': {
                'source': '/test/source',
                'target': '/test/target'
            },
            'credentials': {
                'javdb': {
                    'username': 'testuser',
                    'password': 'testpass'
                }
            },
            'scraping': {
                'max_concurrent_files': 5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            config = manager.get_config()
            
            assert isinstance(config, Config)
            assert config.source_directory == '/test/source'
            assert config.target_directory == '/test/target'
            assert config.javdb_username == 'testuser'
            assert config.javdb_password == 'testpass'
            assert config.max_concurrent_files == 5
        finally:
            os.unlink(temp_path)
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config_data = {
            'directories': {
                'source': '/test/source',
                'target': '/test/target'
            },
            'organization': {
                'naming_pattern': '{actress}/{code}/{code}.{ext}'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            errors = manager.validate_config()
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)
    
    def test_validate_config_errors(self):
        """Test configuration validation with errors."""
        config_data = {
            'directories': {
                'source': '',  # Empty source directory
                'target': '/test/target'
            },
            'organization': {
                'naming_pattern': '{actress}/{invalid}'  # Missing required placeholders
            },
            'scraping': {
                'priority': ['invalid_scraper']  # Invalid scraper
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            errors = manager.validate_config()
            
            assert len(errors) > 0
            error_text = ' '.join(errors)
            assert 'Source directory is required' in error_text or 'source_directory cannot be empty' in error_text
            assert 'Naming pattern must contain {code}' in error_text
            assert 'Invalid scraper in priority list: invalid_scraper' in error_text
        finally:
            os.unlink(temp_path)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        manager = ConfigManager('nonexistent.yaml')
        manager.load_config()  # Load default config
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Remove the temp file so we can test creation
            os.unlink(temp_path)
            
            success = manager.save_config(temp_path)
            assert success is True
            assert Path(temp_path).exists()
            
            # Verify saved content
            with open(temp_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            assert 'directories' in saved_data
            assert 'scraping' in saved_data
        finally:
            if Path(temp_path).exists():
                os.unlink(temp_path)
    
    def test_reload_config(self):
        """Test reloading configuration."""
        config_data = {
            'directories': {
                'source': '/original/source',
                'target': '/original/target'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(temp_path)
            original_config = manager.load_config()
            assert original_config['directories']['source'] == '/original/source'
            
            # Modify the file
            new_config_data = {
                'directories': {
                    'source': '/modified/source',
                    'target': '/modified/target'
                }
            }
            with open(temp_path, 'w') as f:
                yaml.dump(new_config_data, f)
            
            # Reload and verify changes
            manager.reload_config()
            reloaded_config = manager.load_config()
            assert reloaded_config['directories']['source'] == '/modified/source'
        finally:
            os.unlink(temp_path)