#!/usr/bin/env python3
"""
Configuration validation script.

This script validates the configuration file and reports any errors.
"""

import sys
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.config_manager import ConfigManager


def main():
    """Main function for config validation."""
    parser = argparse.ArgumentParser(description='Validate AV Scraper configuration')
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (default: config/config.yaml)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize config manager
        config_manager = ConfigManager(args.config)
        
        if args.verbose:
            print(f"Using config file: {config_manager.config_file}")
        
        # Load and validate configuration
        config_manager.load_config()
        errors = config_manager.validate_config()
        
        if not errors:
            print("✅ Configuration is valid!")
            
            if args.verbose:
                config = config_manager.get_config()
                print(f"\nConfiguration summary:")
                print(f"  Source directory: {config.source_directory}")
                print(f"  Target directory: {config.target_directory}")
                print(f"  Max concurrent files: {config.max_concurrent_files}")
                print(f"  Scraper priority: {', '.join(config.scraper_priority)}")
                print(f"  Headless browser: {config.headless_browser}")
                print(f"  Log level: {config.log_level}")
            
            return 0
        else:
            print("❌ Configuration validation failed:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            return 1
            
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {args.config or 'config/config.yaml'}")
        print("   Create a config file based on config/config.yaml.example")
        return 1
    except Exception as e:
        print(f"❌ Error validating configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())