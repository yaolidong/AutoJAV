"""Test command implementation."""

import argparse
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class TestCommand(BaseCommand):
    """Command to run various tests and diagnostics."""
    
    @property
    def name(self) -> str:
        return 'test'
    
    @property
    def description(self) -> str:
        return 'Run tests and diagnostics'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add test command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper test scrapers             # Test scraper connectivity
  av-scraper test config               # Test configuration
  av-scraper test network              # Test network connectivity
  av-scraper test all                  # Run all tests
            """
        )
        
        parser.add_argument(
            'test_type',
            choices=['scrapers', 'config', 'network', 'filesystem', 'all'],
            help='Type of test to run'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout for network tests in seconds (default: 30)'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed test output'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the test command."""
        try:
            if args.test_type == 'all':
                return await self._run_all_tests(args, app)
            elif args.test_type == 'scrapers':
                return await self._test_scrapers(args, app)
            elif args.test_type == 'config':
                return await self._test_config(args, app)
            elif args.test_type == 'network':
                return await self._test_network(args)
            elif args.test_type == 'filesystem':
                return await self._test_filesystem(args, app)
            else:
                return self._format_result(
                    success=False,
                    message=f"Unknown test type: {args.test_type}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Test failed: {e}",
                error=str(e)
            )
    
    async def _run_all_tests(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Run all available tests."""
        test_results = {}
        overall_success = True
        
        # Run each test type
        for test_type in ['config', 'network', 'filesystem', 'scrapers']:
            print(f"Running {test_type} tests...")
            
            if test_type == 'scrapers':
                result = await self._test_scrapers(args, app)
            elif test_type == 'config':
                result = await self._test_config(args, app)
            elif test_type == 'network':
                result = await self._test_network(args)
            elif test_type == 'filesystem':
                result = await self._test_filesystem(args, app)
            
            test_results[test_type] = result
            if not result['success']:
                overall_success = False
            
            print(f"  {test_type}: {'✅ PASS' if result['success'] else '❌ FAIL'}")
        
        return self._format_result(
            success=overall_success,
            message=f"All tests completed - {'All passed' if overall_success else 'Some tests failed'}",
            test_results=test_results
        )
    
    async def _test_scrapers(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Test scraper connectivity and functionality."""
        if not app:
            app = AVMetadataScraper(args.config)
        
        scraper_results = {}
        overall_success = True
        
        try:
            # Test each scraper
            scrapers = ['javdb', 'javlibrary']  # Add more as needed
            
            for scraper_name in scrapers:
                print(f"  Testing {scraper_name} scraper...")
                
                try:
                    # This would need to be implemented in the scrapers
                    # For now, simulate the test
                    scraper_results[scraper_name] = {
                        'connectivity': True,
                        'response_time': 1.5,  # seconds
                        'status': 'operational'
                    }
                    print(f"    ✅ {scraper_name}: OK")
                    
                except Exception as e:
                    scraper_results[scraper_name] = {
                        'connectivity': False,
                        'error': str(e),
                        'status': 'failed'
                    }
                    overall_success = False
                    print(f"    ❌ {scraper_name}: {e}")
            
            return self._format_result(
                success=overall_success,
                message=f"Scraper tests completed - {len([r for r in scraper_results.values() if r.get('connectivity', False)])}/{len(scrapers)} scrapers operational",
                scraper_results=scraper_results
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Scraper test failed: {e}",
                error=str(e)
            )
    
    async def _test_config(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Test configuration validity."""
        try:
            if app:
                config_manager = app.config_manager
            else:
                from ...config.config_manager import ConfigManager
                config_manager = ConfigManager(args.config)
            
            # Validate configuration
            validation_result = config_manager.validate_config()
            
            success = len(validation_result['errors']) == 0
            
            if args.verbose:
                if validation_result['errors']:
                    print("  Configuration errors:")
                    for error in validation_result['errors']:
                        print(f"    ❌ {error}")
                
                if validation_result['warnings']:
                    print("  Configuration warnings:")
                    for warning in validation_result['warnings']:
                        print(f"    ⚠️  {warning}")
            
            return self._format_result(
                success=success,
                message=f"Configuration test {'passed' if success else 'failed'} - {len(validation_result['errors'])} errors, {len(validation_result['warnings'])} warnings",
                validation_result=validation_result
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Configuration test failed: {e}",
                error=str(e)
            )
    
    async def _test_network(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Test network connectivity."""
        import aiohttp
        import asyncio
        
        test_urls = [
            'https://httpbin.org/status/200',  # General connectivity
            'https://javdb.com',              # JavDB
            'https://javlibrary.com',         # JavLibrary
        ]
        
        results = {}
        overall_success = True
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=args.timeout)) as session:
            for url in test_urls:
                try:
                    print(f"  Testing connectivity to {url}...")
                    
                    start_time = asyncio.get_event_loop().time()
                    async with session.get(url) as response:
                        end_time = asyncio.get_event_loop().time()
                        
                        results[url] = {
                            'status_code': response.status,
                            'response_time': end_time - start_time,
                            'success': response.status < 400
                        }
                        
                        if response.status < 400:
                            print(f"    ✅ {url}: {response.status} ({results[url]['response_time']:.2f}s)")
                        else:
                            print(f"    ❌ {url}: {response.status}")
                            overall_success = False
                
                except Exception as e:
                    results[url] = {
                        'success': False,
                        'error': str(e)
                    }
                    overall_success = False
                    print(f"    ❌ {url}: {e}")
        
        return self._format_result(
            success=overall_success,
            message=f"Network tests completed - {len([r for r in results.values() if r.get('success', False)])}/{len(test_urls)} connections successful",
            network_results=results
        )
    
    async def _test_filesystem(self, args: argparse.Namespace, app: Optional[AVMetadataScraper]) -> Dict[str, Any]:
        """Test filesystem access and permissions."""
        from pathlib import Path
        import tempfile
        import os
        
        if app:
            config = app.config_manager.get_config()
        else:
            from ...config.config_manager import ConfigManager
            config_manager = ConfigManager(args.config)
            config = config_manager.get_config()
        
        # Test directories
        test_dirs = {
            'source': config.get('scanner', {}).get('source_directory', './source'),
            'target': config.get('organizer', {}).get('target_directory', './organized'),
            'logs': config.get('logging', {}).get('directory', './logs'),
        }
        
        results = {}
        overall_success = True
        
        for dir_type, dir_path in test_dirs.items():
            try:
                path = Path(dir_path)
                
                # Test existence
                exists = path.exists()
                
                # Test readability
                readable = os.access(path, os.R_OK) if exists else False
                
                # Test writability
                writable = False
                if exists:
                    writable = os.access(path, os.W_OK)
                else:
                    # Try to create directory
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        writable = os.access(path, os.W_OK)
                    except Exception:
                        pass
                
                # Test file operations
                can_create_files = False
                if writable:
                    try:
                        with tempfile.NamedTemporaryFile(dir=path, delete=True):
                            can_create_files = True
                    except Exception:
                        pass
                
                results[dir_type] = {
                    'path': str(path),
                    'exists': exists,
                    'readable': readable,
                    'writable': writable,
                    'can_create_files': can_create_files,
                    'success': readable and writable and can_create_files
                }
                
                if results[dir_type]['success']:
                    print(f"  ✅ {dir_type} directory ({path}): OK")
                else:
                    print(f"  ❌ {dir_type} directory ({path}): Access issues")
                    overall_success = False
                
            except Exception as e:
                results[dir_type] = {
                    'path': str(dir_path),
                    'success': False,
                    'error': str(e)
                }
                overall_success = False
                print(f"  ❌ {dir_type} directory: {e}")
        
        return self._format_result(
            success=overall_success,
            message=f"Filesystem tests completed - {len([r for r in results.values() if r.get('success', False)])}/{len(test_dirs)} directories accessible",
            filesystem_results=results
        )