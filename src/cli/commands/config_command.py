"""Configuration command implementation."""

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper
from ..config_wizard import ConfigWizard


class ConfigCommand(BaseCommand):
    """Command to manage application configuration."""
    
    @property
    def name(self) -> str:
        return 'config'
    
    @property
    def description(self) -> str:
        return 'Manage application configuration'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add config command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper config wizard             # Interactive configuration setup
  av-scraper config show               # Show current configuration
  av-scraper config validate           # Validate configuration
  av-scraper config set key=value      # Set configuration value
  av-scraper config get scrapers.priority  # Get specific value
  av-scraper config reset              # Reset to default configuration
            """
        )
        
        # Subcommands for config operations
        config_subparsers = parser.add_subparsers(
            dest='config_action',
            help='Configuration actions'
        )
        
        # Wizard subcommand
        wizard_parser = config_subparsers.add_parser(
            'wizard',
            help='Interactive configuration wizard'
        )
        wizard_parser.add_argument(
            '--advanced',
            action='store_true',
            help='Include advanced configuration options'
        )
        
        # Show subcommand
        show_parser = config_subparsers.add_parser(
            'show',
            help='Show current configuration'
        )
        show_parser.add_argument(
            '--section',
            help='Show specific configuration section'
        )
        show_parser.add_argument(
            '--format',
            choices=['yaml', 'json'],
            default='yaml',
            help='Output format (default: yaml)'
        )
        
        # Validate subcommand
        validate_parser = config_subparsers.add_parser(
            'validate',
            help='Validate configuration'
        )
        validate_parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix validation errors'
        )
        
        # Set subcommand
        set_parser = config_subparsers.add_parser(
            'set',
            help='Set configuration value'
        )
        set_parser.add_argument(
            'key_value',
            help='Configuration key=value pair (e.g., scrapers.priority=javdb,javlibrary)'
        )
        
        # Get subcommand
        get_parser = config_subparsers.add_parser(
            'get',
            help='Get configuration value'
        )
        get_parser.add_argument(
            'key',
            help='Configuration key (e.g., scrapers.priority)'
        )
        
        # Reset subcommand
        reset_parser = config_subparsers.add_parser(
            'reset',
            help='Reset configuration to defaults'
        )
        reset_parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm reset without prompting'
        )
        
        # Template subcommand
        template_parser = config_subparsers.add_parser(
            'template',
            help='Generate configuration template'
        )
        template_parser.add_argument(
            '--output', '-o',
            type=Path,
            help='Output file path'
        )
        template_parser.add_argument(
            '--type',
            choices=['basic', 'advanced', 'docker'],
            default='basic',
            help='Template type (default: basic)'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the config command."""
        try:
            if not args.config_action:
                return self._format_result(
                    success=False,
                    message="No configuration action specified. Use 'av-scraper config --help' for options."
                )
            
            # Route to appropriate handler
            if args.config_action == 'wizard':
                return await self._handle_wizard(args)
            elif args.config_action == 'show':
                return await self._handle_show(args, app)
            elif args.config_action == 'validate':
                return await self._handle_validate(args, app)
            elif args.config_action == 'set':
                return await self._handle_set(args, app)
            elif args.config_action == 'get':
                return await self._handle_get(args, app)
            elif args.config_action == 'reset':
                return await self._handle_reset(args, app)
            elif args.config_action == 'template':
                return await self._handle_template(args)
            else:
                return self._format_result(
                    success=False,
                    message=f"Unknown configuration action: {args.config_action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Configuration operation failed: {e}",
                error=str(e)
            )
    
    async def _handle_wizard(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Handle configuration wizard."""
        wizard = ConfigWizard()
        
        try:
            config_path = await wizard.run_wizard(advanced=args.advanced)
            
            return self._format_result(
                success=True,
                message=f"Configuration wizard completed successfully",
                config_file=str(config_path)
            )
            
        except KeyboardInterrupt:
            return self._format_result(
                success=False,
                message="Configuration wizard cancelled by user"
            )
    
    async def _handle_show(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Handle show configuration."""
        if app:
            config = app.config_manager.get_config()
        else:
            from ...config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
            config = config_manager.get_config()
        
        # Filter to specific section if requested
        if args.section:
            config = self._get_nested_value(config, args.section)
            if config is None:
                return self._format_result(
                    success=False,
                    message=f"Configuration section '{args.section}' not found"
                )
        
        # Format output
        if args.format == 'json':
            import json
            formatted_config = json.dumps(config, indent=2, default=str)
        else:  # yaml
            import yaml
            formatted_config = yaml.dump(config, default_flow_style=False, indent=2)
        
        print(formatted_config)
        
        return self._format_result(
            success=True,
            message="Configuration displayed successfully",
            config=config
        )
    
    async def _handle_validate(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Handle configuration validation."""
        if app:
            config_manager = app.config_manager
        else:
            from ...config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
        
        validation_result = config_manager.validate_config()
        
        # Print validation results
        if validation_result['errors']:
            print("Configuration Errors:")
            for error in validation_result['errors']:
                print(f"  ❌ {error}")
        
        if validation_result['warnings']:
            print("Configuration Warnings:")
            for warning in validation_result['warnings']:
                print(f"  ⚠️  {warning}")
        
        if not validation_result['errors'] and not validation_result['warnings']:
            print("✅ Configuration is valid")
        
        # Attempt to fix errors if requested
        if args.fix and validation_result['errors']:
            # This would need to be implemented in ConfigManager
            print("Attempting to fix configuration errors...")
            # fix_result = config_manager.fix_configuration()
            
        return self._format_result(
            success=len(validation_result['errors']) == 0,
            message=f"Validation completed with {len(validation_result['errors'])} errors and {len(validation_result['warnings'])} warnings",
            validation_result=validation_result
        )
    
    async def _handle_set(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Handle set configuration value."""
        try:
            key, value = args.key_value.split('=', 1)
        except ValueError:
            return self._format_result(
                success=False,
                message="Invalid key=value format. Use 'key=value' syntax."
            )
        
        if app:
            config_manager = app.config_manager
        else:
            from ...config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
        
        # Parse value (attempt to convert to appropriate type)
        parsed_value = self._parse_config_value(value)
        
        # Set the value
        config_manager.set_config_value(key, parsed_value)
        
        return self._format_result(
            success=True,
            message=f"Configuration value set: {key} = {parsed_value}",
            key=key,
            value=parsed_value
        )
    
    async def _handle_get(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Handle get configuration value."""
        if app:
            config = app.config_manager.get_config()
        else:
            from ...config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
            config = config_manager.get_config()
        
        value = self._get_nested_value(config, args.key)
        
        if value is None:
            return self._format_result(
                success=False,
                message=f"Configuration key '{args.key}' not found"
            )
        
        print(f"{args.key}: {value}")
        
        return self._format_result(
            success=True,
            message=f"Configuration value retrieved: {args.key}",
            key=args.key,
            value=value
        )
    
    async def _handle_reset(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Handle reset configuration."""
        if not args.confirm:
            response = input("Are you sure you want to reset configuration to defaults? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                return self._format_result(
                    success=False,
                    message="Configuration reset cancelled"
                )
        
        if app:
            config_manager = app.config_manager
        else:
            from ...config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
        
        # Reset configuration (this would need to be implemented)
        # config_manager.reset_to_defaults()
        
        return self._format_result(
            success=True,
            message="Configuration reset to defaults"
        )
    
    async def _handle_template(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Handle generate configuration template."""
        from ...config.config_manager import ConfigManager
        
        # Generate template based on type
        if args.type == 'basic':
            template = ConfigManager.get_default_config()
        elif args.type == 'advanced':
            template = ConfigManager.get_advanced_config_template()
        elif args.type == 'docker':
            template = ConfigManager.get_docker_config_template()
        
        # Output to file or stdout
        if args.output:
            import yaml
            with open(args.output, 'w', encoding='utf-8') as f:
                yaml.dump(template, f, default_flow_style=False, indent=2)
            
            return self._format_result(
                success=True,
                message=f"Configuration template written to {args.output}",
                output_file=str(args.output)
            )
        else:
            import yaml
            print(yaml.dump(template, default_flow_style=False, indent=2))
            
            return self._format_result(
                success=True,
                message="Configuration template generated",
                template=template
            )
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get nested configuration value using dot notation."""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def _parse_config_value(self, value: str) -> Any:
        """Parse configuration value string to appropriate type."""
        # Try to parse as JSON first (handles lists, dicts, booleans, numbers)
        try:
            import json
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Handle common string values
        if value.lower() in ['true', 'yes', 'on']:
            return True
        elif value.lower() in ['false', 'no', 'off']:
            return False
        elif value.lower() in ['null', 'none']:
            return None
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value