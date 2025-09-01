"""Tests for CLI functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import json

from src.cli.cli_main import AVScraperCLI
from src.cli.commands.scan_command import ScanCommand
from src.cli.commands.config_command import ConfigCommand
from src.cli.commands.test_command import TestCommand
from src.cli.config_wizard import ConfigWizard


class TestAVScraperCLI:
    """Test cases for the main CLI class."""
    
    def test_cli_initialization(self):
        """Test CLI initialization."""
        cli = AVScraperCLI()
        
        assert cli.app is None
        assert cli.commands is not None
        assert len(cli.commands) > 0
        
        # Check that all expected commands are registered
        expected_commands = ['scan', 'process', 'status', 'config', 'test', 'health', 'stats']
        for command in expected_commands:
            assert command in cli.commands
    
    def test_parser_creation(self):
        """Test argument parser creation."""
        cli = AVScraperCLI()
        parser = cli.create_parser()
        
        assert parser is not None
        assert parser.prog == 'av-scraper'
        
        # Test that parser can handle basic arguments
        args = parser.parse_args(['--help'])
        # This would normally exit, but we're just testing structure
    
    @pytest.mark.asyncio
    async def test_run_with_no_command(self):
        """Test running CLI with no command."""
        cli = AVScraperCLI()
        
        # Mock print to capture help output
        with patch('builtins.print') as mock_print:
            result = await cli.run([])
            assert result == 0
            # Should have printed help


class TestScanCommand:
    """Test cases for the scan command."""
    
    def test_scan_command_properties(self):
        """Test scan command properties."""
        command = ScanCommand()
        
        assert command.name == 'scan'
        assert command.description is not None
        assert len(command.description) > 0
    
    def test_scan_command_parser(self):
        """Test scan command parser creation."""
        command = ScanCommand()
        
        # Create a mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser
        
        parser = command.add_parser(mock_subparsers)
        
        # Verify parser was created
        mock_subparsers.add_parser.assert_called_once()
        assert parser == mock_parser
    
    @pytest.mark.asyncio
    async def test_scan_command_execution(self):
        """Test scan command execution."""
        command = ScanCommand()
        
        # Create mock app and args
        mock_app = Mock()
        mock_app._scan_files = AsyncMock(return_value=[])
        
        mock_args = Mock()
        mock_args.source = None
        mock_args.format = 'list'
        mock_args.show_codes = False
        mock_args.show_sizes = False
        mock_args.show_paths = False
        mock_args.sort_by = 'name'
        mock_args.reverse = False
        mock_args.limit = None
        mock_args.export = None
        
        result = await command.execute(mock_args, mock_app)
        
        assert result['success'] is True
        assert 'files_found' in result
        assert result['files_found'] == 0


class TestConfigCommand:
    """Test cases for the config command."""
    
    def test_config_command_properties(self):
        """Test config command properties."""
        command = ConfigCommand()
        
        assert command.name == 'config'
        assert command.description is not None
    
    @pytest.mark.asyncio
    async def test_config_show_command(self):
        """Test config show subcommand."""
        command = ConfigCommand()
        
        # Mock app with config
        mock_app = Mock()
        mock_app.config_manager.get_config.return_value = {
            'test': 'value',
            'nested': {'key': 'value'}
        }
        
        mock_args = Mock()
        mock_args.config_action = 'show'
        mock_args.section = None
        mock_args.format = 'yaml'
        
        with patch('builtins.print') as mock_print:
            result = await command.execute(mock_args, mock_app)
            
            assert result['success'] is True
            mock_print.assert_called()
    
    @pytest.mark.asyncio
    async def test_config_template_command(self):
        """Test config template subcommand."""
        command = ConfigCommand()
        
        mock_args = Mock()
        mock_args.config_action = 'template'
        mock_args.type = 'basic'
        mock_args.output = None
        
        with patch('src.cli.commands.config_command.ConfigManager') as mock_config_manager:
            mock_config_manager.get_default_config.return_value = {'test': 'config'}
            
            with patch('builtins.print') as mock_print:
                result = await command.execute(mock_args, None)
                
                assert result['success'] is True
                mock_print.assert_called()


class TestTestCommand:
    """Test cases for the test command."""
    
    def test_test_command_properties(self):
        """Test test command properties."""
        command = TestCommand()
        
        assert command.name == 'test'
        assert command.description is not None
    
    @pytest.mark.asyncio
    async def test_network_test(self):
        """Test network connectivity test."""
        command = TestCommand()
        
        mock_args = Mock()
        mock_args.test_type = 'network'
        mock_args.timeout = 10
        mock_args.verbose = False
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_instance = Mock()
            mock_session_instance.get.return_value = mock_response
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance
            
            with patch('builtins.print'):
                result = await command.execute(mock_args, None)
                
                assert result['success'] is True
                assert 'network_results' in result
    
    @pytest.mark.asyncio
    async def test_config_test(self):
        """Test configuration validation test."""
        command = TestCommand()
        
        mock_args = Mock()
        mock_args.test_type = 'config'
        mock_args.config = None
        mock_args.verbose = False
        
        with patch('src.cli.commands.test_command.ConfigManager') as mock_config_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.validate_config.return_value = {
                'errors': [],
                'warnings': []
            }
            mock_config_manager.return_value = mock_manager_instance
            
            result = await command.execute(mock_args, None)
            
            assert result['success'] is True
            assert 'validation_result' in result


class TestConfigWizard:
    """Test cases for the configuration wizard."""
    
    def test_wizard_initialization(self):
        """Test wizard initialization."""
        wizard = ConfigWizard()
        
        assert wizard.config == {}
        assert wizard.advanced_mode is False
    
    @pytest.mark.asyncio
    async def test_wizard_save_configuration(self):
        """Test configuration saving."""
        wizard = ConfigWizard()
        wizard.config = {
            'scanner': {'source_directory': '/test'},
            'organizer': {'target_directory': '/test/organized'}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'test_config.yaml'
            
            # Mock input to return the test path
            with patch('builtins.input', return_value=str(config_path)):
                result_path = await wizard._save_configuration()
                
                assert result_path == config_path
                assert config_path.exists()
                
                # Verify content
                import yaml
                with open(config_path, 'r') as f:
                    saved_config = yaml.safe_load(f)
                
                assert 'scanner' in saved_config
                assert saved_config['scanner']['source_directory'] == '/test'


class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
    @pytest.mark.asyncio
    async def test_cli_help_command(self):
        """Test CLI help command integration."""
        cli = AVScraperCLI()
        
        # Test main help
        with patch('builtins.print') as mock_print:
            result = await cli.run(['--help'])
            assert result == 0
            mock_print.assert_called()
    
    @pytest.mark.asyncio
    async def test_cli_version_command(self):
        """Test CLI version command."""
        cli = AVScraperCLI()
        
        with patch('builtins.print') as mock_print:
            try:
                await cli.run(['--version'])
            except SystemExit as e:
                # argparse calls sys.exit for --version
                assert e.code == 0
    
    @pytest.mark.asyncio
    async def test_cli_json_output(self):
        """Test CLI JSON output format."""
        cli = AVScraperCLI()
        
        # Mock a command that returns a dict
        mock_command = Mock()
        mock_command.execute = AsyncMock(return_value={'test': 'result'})
        cli.commands['test_cmd'] = mock_command
        
        with patch('builtins.print') as mock_print:
            result = await cli.run(['test_cmd', '--json'])
            
            # Should have printed JSON
            mock_print.assert_called()
            # Get the printed JSON
            printed_args = mock_print.call_args[0]
            json_output = json.loads(printed_args[0])
            assert json_output['test'] == 'result'
    
    @pytest.mark.asyncio
    async def test_cli_error_handling(self):
        """Test CLI error handling."""
        cli = AVScraperCLI()
        
        # Mock a command that raises an exception
        mock_command = Mock()
        mock_command.execute = AsyncMock(side_effect=Exception("Test error"))
        cli.commands['error_cmd'] = mock_command
        
        result = await cli.run(['error_cmd'])
        assert result == 1  # Should return error code
    
    @pytest.mark.asyncio
    async def test_cli_keyboard_interrupt(self):
        """Test CLI keyboard interrupt handling."""
        cli = AVScraperCLI()
        
        # Mock a command that raises KeyboardInterrupt
        mock_command = Mock()
        mock_command.execute = AsyncMock(side_effect=KeyboardInterrupt())
        cli.commands['interrupt_cmd'] = mock_command
        
        result = await cli.run(['interrupt_cmd'])
        assert result == 130  # Standard SIGINT exit code


if __name__ == "__main__":
    pytest.main([__file__])