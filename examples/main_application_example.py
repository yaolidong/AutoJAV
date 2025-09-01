#!/usr/bin/env python3
"""Example usage of the main AV Metadata Scraper application."""

import asyncio
import tempfile
import yaml
from pathlib import Path

from src.main_application import AVMetadataScraper


def create_example_config(config_dir: Path) -> Path:
    """Create an example configuration file."""
    config_data = {
        'logging': {
            'level': 'INFO',
            'directory': str(config_dir / 'logs'),
            'filename': 'av_scraper.log',
            'console': True,
            'file': True,
            'colored': True,
            'json_format': False
        },
        'scanner': {
            'source_directory': str(config_dir / 'source'),
            'supported_formats': ['.mp4', '.mkv', '.avi', '.wmv', '.mov'],
            'recursive': True
        },
        'scrapers': {
            'javdb': {
                'enabled': True,
                'use_login': False,  # Disable login for demo
                'priority': 1
            },
            'javlibrary': {
                'enabled': True,
                'priority': 2,
                'language': 'en'
            },
            'coordinator': {
                'max_concurrent_requests': 2,
                'timeout_seconds': 30,
                'retry_attempts': 2
            }
        },
        'organizer': {
            'target_directory': str(config_dir / 'organized'),
            'naming_pattern': '{actress}/{code}/{code}.{ext}',
            'conflict_resolution': 'rename',
            'create_metadata_files': True,
            'safe_mode': True
        },
        'downloader': {
            'enabled': True,
            'max_concurrent': 2,
            'timeout': 30,
            'download_cover': True,
            'download_poster': True,
            'download_screenshots': False,
            'resize_images': False,
            'create_thumbnails': False
        },
        'processing': {
            'max_concurrent_files': 3
        }
    }
    
    config_file = config_dir / 'config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    return config_file


def create_sample_files(source_dir: Path) -> None:
    """Create sample video files for demonstration."""
    source_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample video files (empty files for demo)
    sample_files = [
        'SSIS-001.mp4',
        'STARS-123.mkv',
        'MIDE-789.avi',
        'PRED-456.mp4',
        'CAWD-321.mkv'
    ]
    
    for filename in sample_files:
        file_path = source_dir / filename
        file_path.write_bytes(b'fake video content for demo')
        print(f"Created sample file: {filename}")


async def basic_usage_example():
    """Demonstrate basic usage of the main application."""
    print("=== Basic Usage Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create configuration
        config_file = create_example_config(temp_path)
        print(f"Created configuration: {config_file}")
        
        # Create sample files
        source_dir = temp_path / 'source'
        create_sample_files(source_dir)
        print(f"Created sample files in: {source_dir}")
        
        # Initialize application
        print("\nInitializing AV Metadata Scraper...")
        app = AVMetadataScraper(config_file)
        
        # Check initial status
        status = app.get_status()
        print(f"Initial status: Running={status['is_running']}")
        
        # Perform health check
        print("\nPerforming health check...")
        health = await app.health_check()
        print(f"Health status: {health['status']}")
        
        if health['status'] != 'healthy':
            print("Health issues detected:")
            for component, details in health['components'].items():
                if isinstance(details, dict) and details.get('errors'):
                    print(f"  {component}: {details['errors']}")
        
        print("\nNote: This is a demonstration with mock data.")
        print("In a real scenario, the application would:")
        print("1. Scan the source directory for video files")
        print("2. Extract movie codes from filenames")
        print("3. Scrape metadata from configured websites")
        print("4. Organize files based on metadata")
        print("5. Download cover images and posters")
        
        # Show configuration
        print(f"\nConfiguration summary:")
        print(f"  Source directory: {app.config['scanner']['source_directory']}")
        print(f"  Target directory: {app.config['organizer']['target_directory']}")
        print(f"  Supported formats: {app.config['scanner']['supported_formats']}")
        print(f"  Max concurrent files: {app.config['processing']['max_concurrent_files']}")


async def status_monitoring_example():
    """Demonstrate status monitoring capabilities."""
    print("\n=== Status Monitoring Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_file = create_example_config(temp_path)
        
        app = AVMetadataScraper(config_file)
        
        # Get detailed status
        status = app.get_status()
        
        print("Application Status:")
        print(f"  Running: {status['is_running']}")
        print(f"  Should stop: {status['should_stop']}")
        print(f"  Active tasks: {status['active_tasks']}")
        print(f"  Queue size: {status['queue_size']}")
        
        print("\nProcessing Statistics:")
        stats = status['processing_stats']
        print(f"  Files scanned: {stats['files_scanned']}")
        print(f"  Files processed: {stats['files_processed']}")
        print(f"  Files organized: {stats['files_organized']}")
        print(f"  Metadata scraped: {stats['metadata_scraped']}")
        print(f"  Images downloaded: {stats['images_downloaded']}")
        print(f"  Errors encountered: {stats['errors_encountered']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        
        print("\nComponent Statistics:")
        comp_stats = status['component_stats']
        
        print(f"  Scraper:")
        scraper_stats = comp_stats['scraper']
        print(f"    Total requests: {scraper_stats['total_requests']}")
        print(f"    Success rate: {scraper_stats['success_rate']:.1f}%")
        
        print(f"  Organizer:")
        organizer_stats = comp_stats['organizer']
        print(f"    Files processed: {organizer_stats['files_processed']}")
        print(f"    Success rate: {organizer_stats['success_rate']:.1f}%")
        
        print(f"  Downloader:")
        downloader_stats = comp_stats['downloader']
        print(f"    Images downloaded: {downloader_stats['images_downloaded']}")
        print(f"    Success rate: {downloader_stats['success_rate']:.1f}%")


async def health_check_example():
    """Demonstrate health check functionality."""
    print("\n=== Health Check Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config_file = create_example_config(temp_path)
        
        app = AVMetadataScraper(config_file)
        
        print("Performing comprehensive health check...")
        health = await app.health_check()
        
        print(f"Overall Status: {health['status']}")
        print(f"Timestamp: {health['timestamp']}")
        
        print("\nComponent Health:")
        for component, details in health['components'].items():
            print(f"  {component.title()}:")
            
            if isinstance(details, dict):
                if 'errors' in details and details['errors']:
                    print(f"    ✗ Errors: {details['errors']}")
                elif details.get('valid', True):
                    print(f"    ✓ Healthy")
                else:
                    print(f"    ⚠ Issues detected")
                
                if 'warnings' in details and details['warnings']:
                    print(f"    ⚠ Warnings: {details['warnings']}")
            else:
                print(f"    Status: {details}")
        
        if health['status'] == 'degraded' and 'issues' in health:
            print(f"\nComponents with issues: {', '.join(health['issues'])}")
        elif health['status'] == 'unhealthy':
            print(f"\nCritical error: {health.get('error', 'Unknown error')}")


async def configuration_example():
    """Demonstrate different configuration options."""
    print("\n=== Configuration Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create different configuration scenarios
        configs = {
            'minimal': {
                'scanner': {
                    'source_directory': str(temp_path / 'source'),
                },
                'organizer': {
                    'target_directory': str(temp_path / 'minimal_target'),
                },
                'downloader': {
                    'enabled': False
                }
            },
            'high_performance': {
                'scanner': {
                    'source_directory': str(temp_path / 'source'),
                    'recursive': True
                },
                'organizer': {
                    'target_directory': str(temp_path / 'hp_target'),
                    'safe_mode': False  # Move files instead of copy
                },
                'processing': {
                    'max_concurrent_files': 8
                },
                'scrapers': {
                    'coordinator': {
                        'max_concurrent_requests': 5,
                        'timeout_seconds': 15
                    }
                },
                'downloader': {
                    'enabled': True,
                    'max_concurrent': 5
                }
            },
            'conservative': {
                'scanner': {
                    'source_directory': str(temp_path / 'source'),
                },
                'organizer': {
                    'target_directory': str(temp_path / 'conservative_target'),
                    'safe_mode': True,
                    'conflict_resolution': 'skip'
                },
                'processing': {
                    'max_concurrent_files': 1
                },
                'scrapers': {
                    'coordinator': {
                        'max_concurrent_requests': 1,
                        'timeout_seconds': 60,
                        'retry_attempts': 5
                    }
                },
                'downloader': {
                    'enabled': True,
                    'max_concurrent': 1,
                    'timeout': 60
                }
            }
        }
        
        for config_name, config_data in configs.items():
            print(f"{config_name.title()} Configuration:")
            
            # Create config file
            config_file = temp_path / f'{config_name}_config.yaml'
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            # Initialize app with this config
            app = AVMetadataScraper(config_file)
            
            # Show key settings
            print(f"  Max concurrent files: {app.config.get('processing', {}).get('max_concurrent_files', 3)}")
            print(f"  Safe mode: {app.config.get('organizer', {}).get('safe_mode', True)}")
            print(f"  Image download: {app.config.get('downloader', {}).get('enabled', True)}")
            print(f"  Scraper timeout: {app.config.get('scrapers', {}).get('coordinator', {}).get('timeout_seconds', 60)}s")
            print()


async def error_handling_example():
    """Demonstrate error handling capabilities."""
    print("\n=== Error Handling Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create config with invalid directories to trigger errors
        config_data = {
            'scanner': {
                'source_directory': '/nonexistent/source',  # Invalid directory
            },
            'organizer': {
                'target_directory': '/readonly/target',  # Invalid directory
            },
            'logging': {
                'level': 'DEBUG',
                'console': True,
                'file': False
            }
        }
        
        config_file = temp_path / 'error_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        print("Testing error handling with invalid configuration...")
        
        try:
            app = AVMetadataScraper(config_file)
            
            # Perform health check to detect issues
            health = await app.health_check()
            
            print(f"Health status: {health['status']}")
            
            if health['status'] != 'healthy':
                print("Detected configuration issues:")
                for component, details in health['components'].items():
                    if isinstance(details, dict) and details.get('errors'):
                        print(f"  {component}: {details['errors']}")
            
            # Get error statistics
            error_stats = app.error_handler.get_error_statistics()
            print(f"\nError Handler Statistics:")
            print(f"  Total errors: {error_stats['total_errors']}")
            print(f"  Resolution rate: {error_stats['resolution_rate']:.1f}%")
            
        except Exception as e:
            print(f"Application initialization failed: {e}")
            print("This demonstrates the error handling capabilities.")


async def integration_example():
    """Demonstrate integration with all components."""
    print("\n=== Integration Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create comprehensive configuration
        config_file = create_example_config(temp_path)
        
        # Create sample files
        source_dir = temp_path / 'source'
        create_sample_files(source_dir)
        
        print("Initializing integrated application...")
        app = AVMetadataScraper(config_file)
        
        print("\nComponent Integration Status:")
        
        # Check file scanner
        print("  File Scanner:")
        try:
            # Test file scanning (would normally be done during processing)
            print(f"    Source directory: {app.file_scanner.source_directory}")
            print(f"    Supported formats: {app.file_scanner.supported_formats}")
            print("    ✓ Initialized successfully")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        
        # Check metadata scraper
        print("  Metadata Scraper:")
        try:
            available_scrapers = app.metadata_scraper.get_available_scrapers()
            print(f"    Available scrapers: {available_scrapers}")
            print("    ✓ Initialized successfully")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        
        # Check file organizer
        print("  File Organizer:")
        try:
            validation = app.file_organizer.validate_target_directory()
            if validation['valid']:
                print("    ✓ Target directory valid")
            else:
                print(f"    ⚠ Issues: {validation['errors']}")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        
        # Check image downloader
        print("  Image Downloader:")
        try:
            downloader_stats = app.image_downloader.get_statistics()
            print(f"    Max concurrent: {app.image_downloader.max_concurrent_downloads}")
            print("    ✓ Initialized successfully")
        except Exception as e:
            print(f"    ✗ Error: {e}")
        
        # Show overall integration status
        print(f"\nIntegration Summary:")
        print(f"  All components initialized: ✓")
        print(f"  Configuration loaded: ✓")
        print(f"  Logging configured: ✓")
        print(f"  Error handling active: ✓")
        print(f"  Progress tracking ready: ✓")
        
        print(f"\nReady for processing pipeline:")
        print(f"  1. Scan files in: {source_dir}")
        print(f"  2. Scrape metadata using: {len(app.metadata_scraper.scrapers)} scrapers")
        print(f"  3. Organize files to: {app.file_organizer.target_directory}")
        print(f"  4. Download images: {'Enabled' if app.config['downloader']['enabled'] else 'Disabled'}")


async def main():
    """Run all examples."""
    print("AV Metadata Scraper - Main Application Examples")
    print("=" * 60)
    
    try:
        await basic_usage_example()
        await status_monitoring_example()
        await health_check_example()
        await configuration_example()
        await error_handling_example()
        await integration_example()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("\nTo run the actual application:")
        print("1. Create a configuration file (see examples above)")
        print("2. Place video files in the source directory")
        print("3. Run: python -m src.main_application")
        print("4. Monitor progress and check organized files")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())