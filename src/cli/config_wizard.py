"""Interactive configuration wizard for AV Metadata Scraper."""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class ConfigWizard:
    """
    Interactive configuration wizard that guides users through setting up
    the AV Metadata Scraper configuration.
    """
    
    def __init__(self):
        """Initialize the configuration wizard."""
        self.config = {}
        self.advanced_mode = False
    
    async def run_wizard(self, advanced: bool = False) -> Path:
        """
        Run the interactive configuration wizard.
        
        Args:
            advanced: Whether to include advanced configuration options
            
        Returns:
            Path to the created configuration file
        """
        self.advanced_mode = advanced
        
        print("🎬 AV Metadata Scraper Configuration Wizard")
        print("=" * 50)
        print("This wizard will help you set up your configuration.")
        print("Press Ctrl+C at any time to cancel.\n")
        
        try:
            # Basic configuration
            await self._configure_directories()
            await self._configure_scrapers()
            await self._configure_organization()
            await self._configure_processing()
            
            # Advanced configuration
            if advanced:
                await self._configure_advanced_options()
            
            # Save configuration
            config_path = await self._save_configuration()
            
            print(f"\n✅ Configuration saved to: {config_path}")
            print("You can now run: av-scraper process")
            
            return config_path
            
        except KeyboardInterrupt:
            print("\n\n❌ Configuration wizard cancelled.")
            raise
    
    async def _configure_directories(self) -> None:
        """Configure directory settings."""
        print("📁 Directory Configuration")
        print("-" * 25)
        
        # Source directory
        while True:
            source_dir = input("Source directory (where your video files are): ").strip()
            if not source_dir:
                print("❌ Source directory is required.")
                continue
            
            source_path = Path(source_dir).expanduser().resolve()
            if not source_path.exists():
                create = input(f"Directory {source_path} doesn't exist. Create it? (y/N): ").lower()
                if create in ['y', 'yes']:
                    try:
                        source_path.mkdir(parents=True, exist_ok=True)
                        print(f"✅ Created directory: {source_path}")
                    except Exception as e:
                        print(f"❌ Failed to create directory: {e}")
                        continue
                else:
                    continue
            
            self.config['scanner'] = {'source_directory': str(source_path)}
            break
        
        # Target directory
        while True:
            default_target = str(Path(source_dir).parent / "organized")
            target_dir = input(f"Target directory for organized files [{default_target}]: ").strip()
            
            if not target_dir:
                target_dir = default_target
            
            target_path = Path(target_dir).expanduser().resolve()
            
            # Create target directory if it doesn't exist
            try:
                target_path.mkdir(parents=True, exist_ok=True)
                self.config['organizer'] = {'target_directory': str(target_path)}
                print(f"✅ Target directory: {target_path}")
                break
            except Exception as e:
                print(f"❌ Failed to create target directory: {e}")
        
        print()
    
    async def _configure_scrapers(self) -> None:
        """Configure scraper settings."""
        print("🔍 Scraper Configuration")
        print("-" * 25)
        
        # Scraper priority
        print("Available scrapers:")
        print("1. JavDB (requires login, more comprehensive)")
        print("2. JavLibrary (no login required, basic info)")
        
        priority_input = input("Scraper priority (1,2 or 2,1) [1,2]: ").strip()
        
        if priority_input == "2,1":
            priority = ["javlibrary", "javdb"]
        else:
            priority = ["javdb", "javlibrary"]
        
        self.config['scrapers'] = {
            'priority': priority,
            'max_concurrent_requests': 2,
            'retry_attempts': 3,
            'timeout': 30
        }
        
        # JavDB credentials (if JavDB is in priority)
        if "javdb" in priority:
            print("\n🔐 JavDB Login (optional but recommended)")
            print("Having a JavDB account provides better results and fewer restrictions.")
            
            use_login = input("Do you have a JavDB account? (y/N): ").lower()
            
            if use_login in ['y', 'yes']:
                username = input("JavDB username: ").strip()
                password = input("JavDB password: ").strip()
                
                if username and password:
                    self.config['scrapers']['javdb'] = {
                        'username': username,
                        'password': password,
                        'use_login': True
                    }
                    print("✅ JavDB credentials configured")
                else:
                    print("⚠️  Skipping JavDB login (empty credentials)")
            else:
                print("ℹ️  JavDB will be used without login (limited functionality)")
        
        print()
    
    async def _configure_organization(self) -> None:
        """Configure file organization settings."""
        print("📋 File Organization")
        print("-" * 20)
        
        # Naming pattern
        print("File naming patterns (use placeholders):")
        print("Available placeholders: {actress}, {code}, {title}, {studio}, {year}, {ext}")
        print("Examples:")
        print("1. {actress}/{code}/{code}.{ext}")
        print("2. {code}/{actress} - {title}.{ext}")
        print("3. {studio}/{year}/{code} - {title}.{ext}")
        
        pattern_choice = input("Choose pattern (1-3) or enter custom [1]: ").strip()
        
        patterns = {
            "1": "{actress}/{code}/{code}.{ext}",
            "2": "{code}/{actress} - {title}.{ext}",
            "3": "{studio}/{year}/{code} - {title}.{ext}"
        }
        
        if pattern_choice in patterns:
            naming_pattern = patterns[pattern_choice]
        elif pattern_choice:
            naming_pattern = pattern_choice
        else:
            naming_pattern = patterns["1"]
        
        # File handling mode
        safe_mode = input("Safe mode (copy files instead of moving)? (Y/n): ").lower()
        safe_mode = safe_mode not in ['n', 'no']
        
        # Metadata files
        save_metadata = input("Save metadata as JSON files? (Y/n): ").lower()
        save_metadata = save_metadata not in ['n', 'no']
        
        self.config['organizer'].update({
            'naming_pattern': naming_pattern,
            'safe_mode': safe_mode,
            'create_metadata_files': save_metadata,
            'conflict_resolution': 'rename'
        })
        
        print(f"✅ Naming pattern: {naming_pattern}")
        print(f"✅ Safe mode: {'Enabled' if safe_mode else 'Disabled'}")
        print(f"✅ Metadata files: {'Enabled' if save_metadata else 'Disabled'}")
        print()
    
    async def _configure_processing(self) -> None:
        """Configure processing settings."""
        print("⚙️  Processing Configuration")
        print("-" * 25)
        
        # Concurrent processing
        max_concurrent = input("Maximum concurrent files to process [2]: ").strip()
        try:
            max_concurrent = int(max_concurrent) if max_concurrent else 2
        except ValueError:
            max_concurrent = 2
        
        # Image downloads
        download_images = input("Download cover images and posters? (Y/n): ").lower()
        download_images = download_images not in ['n', 'no']
        
        image_config = {
            'enabled': download_images,
            'max_concurrent': 3,
            'timeout': 30,
            'download_cover': True,
            'download_poster': True,
            'download_screenshots': False
        }
        
        if download_images:
            download_screenshots = input("Download screenshots? (y/N): ").lower()
            image_config['download_screenshots'] = download_screenshots in ['y', 'yes']
        
        self.config['processing'] = {
            'max_concurrent_files': max_concurrent
        }
        
        self.config['downloader'] = image_config
        
        print(f"✅ Max concurrent files: {max_concurrent}")
        print(f"✅ Image downloads: {'Enabled' if download_images else 'Disabled'}")
        print()
    
    async def _configure_advanced_options(self) -> None:
        """Configure advanced options."""
        print("🔧 Advanced Configuration")
        print("-" * 25)
        
        # Logging configuration
        log_level = input("Log level (DEBUG/INFO/WARNING/ERROR) [INFO]: ").strip().upper()
        if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            log_level = 'INFO'
        
        # Network configuration
        use_proxy = input("Use HTTP proxy? (y/N): ").lower()
        proxy_config = {}
        
        if use_proxy in ['y', 'yes']:
            proxy_url = input("Proxy URL (e.g., http://proxy:8080): ").strip()
            if proxy_url:
                proxy_config['proxy_url'] = proxy_url
        
        # Browser configuration
        headless = input("Run browser in headless mode? (Y/n): ").lower()
        headless = headless not in ['n', 'no']
        
        browser_timeout = input("Browser timeout in seconds [30]: ").strip()
        try:
            browser_timeout = int(browser_timeout) if browser_timeout else 30
        except ValueError:
            browser_timeout = 30
        
        # Update configuration
        self.config['logging'] = {
            'level': log_level,
            'directory': 'logs',
            'filename': 'av_scraper.log',
            'console': True,
            'file': True
        }
        
        if proxy_config:
            self.config['network'] = proxy_config
        
        self.config['browser'] = {
            'headless': headless,
            'timeout': browser_timeout
        }
        
        print(f"✅ Log level: {log_level}")
        print(f"✅ Proxy: {'Configured' if proxy_config else 'None'}")
        print(f"✅ Browser: {'Headless' if headless else 'Visible'}")
        print()
    
    async def _save_configuration(self) -> Path:
        """Save the configuration to file."""
        print("💾 Save Configuration")
        print("-" * 20)
        
        # Default config path
        default_path = Path("config/config.yaml")
        
        config_path_input = input(f"Configuration file path [{default_path}]: ").strip()
        
        if config_path_input:
            config_path = Path(config_path_input)
        else:
            config_path = default_path
        
        # Create directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add some default values that weren't configured
        self._add_default_values()
        
        # Save configuration
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2, sort_keys=False)
        
        return config_path
    
    def _add_default_values(self) -> None:
        """Add default values for unconfigured options."""
        # Scanner defaults
        if 'scanner' not in self.config:
            self.config['scanner'] = {}
        
        scanner_defaults = {
            'supported_formats': ['.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v'],
            'recursive': True,
            'min_file_size': 50 * 1024 * 1024  # 50MB
        }
        
        for key, value in scanner_defaults.items():
            if key not in self.config['scanner']:
                self.config['scanner'][key] = value
        
        # Organizer defaults
        if 'organizer' not in self.config:
            self.config['organizer'] = {}
        
        organizer_defaults = {
            'conflict_resolution': 'rename',
            'safe_mode': True,
            'create_metadata_files': True
        }
        
        for key, value in organizer_defaults.items():
            if key not in self.config['organizer']:
                self.config['organizer'][key] = value
        
        # Processing defaults
        if 'processing' not in self.config:
            self.config['processing'] = {}
        
        processing_defaults = {
            'max_concurrent_files': 2
        }
        
        for key, value in processing_defaults.items():
            if key not in self.config['processing']:
                self.config['processing'][key] = value
        
        # Logging defaults
        if 'logging' not in self.config:
            self.config['logging'] = {
                'level': 'INFO',
                'directory': 'logs',
                'filename': 'av_scraper.log',
                'console': True,
                'file': True
            }
        
        # Browser defaults
        if 'browser' not in self.config:
            self.config['browser'] = {
                'headless': True,
                'timeout': 30
            }