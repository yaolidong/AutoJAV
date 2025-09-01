#!/usr/bin/env python3
"""
Test script for JavDB scraper functionality.

This script tests the JavDBScraper with real JavDB website.
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.webdriver_manager import WebDriverManager
from src.utils.login_manager import LoginManager
from src.scrapers.javdb_scraper import JavDBScraper


async def test_javdb_scraper(
    code: str,
    username: str = None,
    password: str = None,
    headless: bool = True,
    verbose: bool = False
):
    """
    Test JavDB scraper functionality.
    
    Args:
        code: Movie code to search for
        username: JavDB username (optional)
        password: JavDB password (optional)
        headless: Run browser in headless mode
        verbose: Verbose output
    """
    print(f"Testing JavDB Scraper")
    print(f"Movie code: {code}")
    print(f"Headless mode: {headless}")
    print(f"Login: {'Yes' if username else 'No'}")
    print("-" * 40)
    
    try:
        with WebDriverManager(headless=headless, timeout=30) as driver_manager:
            print("✓ WebDriver started successfully")
            
            # Create login manager if credentials provided
            login_manager = None
            if username and password:
                login_manager = LoginManager(
                    username=username,
                    password=password,
                    driver_manager=driver_manager,
                    cookies_file=f"javdb_cookies_{username}.json"
                )
                print("✓ Login manager created")
            
            # Create JavDB scraper
            scraper = JavDBScraper(
                driver_manager=driver_manager,
                login_manager=login_manager,
                use_login=login_manager is not None
            )
            
            print("✓ JavDB scraper created")
            
            # Test availability
            print("Checking JavDB availability...")
            is_available = await scraper.is_available()
            
            if is_available:
                print("✓ JavDB is available")
            else:
                print("✗ JavDB is not available")
                return False
            
            # Test search
            print(f"Searching for movie code: {code}")
            metadata = await scraper.search_movie(code)
            
            if metadata:
                print("✓ Movie found!")
                print("\nMovie Metadata:")
                print(f"  Code: {metadata.code}")
                print(f"  Title: {metadata.title}")
                
                if metadata.title_en:
                    print(f"  English Title: {metadata.title_en}")
                
                if metadata.actresses:
                    print(f"  Actresses: {', '.join(metadata.actresses)}")
                
                if metadata.release_date:
                    print(f"  Release Date: {metadata.release_date}")
                
                if metadata.duration:
                    print(f"  Duration: {metadata.duration_str}")
                
                if metadata.studio:
                    print(f"  Studio: {metadata.studio}")
                
                if metadata.series:
                    print(f"  Series: {metadata.series}")
                
                if metadata.genres:
                    print(f"  Genres: {', '.join(metadata.genres[:5])}{'...' if len(metadata.genres) > 5 else ''}")
                
                if metadata.rating:
                    print(f"  Rating: {metadata.rating}/10")
                
                if metadata.cover_url:
                    print(f"  Cover URL: {metadata.cover_url}")
                
                if metadata.screenshots:
                    print(f"  Screenshots: {len(metadata.screenshots)} found")
                
                if metadata.description and verbose:
                    print(f"  Description: {metadata.description[:200]}{'...' if len(metadata.description) > 200 else ''}")
                
                print(f"  Source URL: {metadata.source_url}")
                print(f"  Scraped at: {metadata.scraped_at}")
                
                # Test metadata validation
                try:
                    # This will raise an exception if metadata is invalid
                    metadata_dict = metadata.to_dict()
                    print("✓ Metadata validation passed")
                    
                    if verbose:
                        print("\nFull metadata dictionary:")
                        for key, value in metadata_dict.items():
                            if isinstance(value, list) and len(value) > 3:
                                print(f"  {key}: [{', '.join(map(str, value[:3]))}, ...] ({len(value)} items)")
                            else:
                                print(f"  {key}: {value}")
                
                except Exception as e:
                    print(f"✗ Metadata validation failed: {e}")
                    return False
                
            else:
                print(f"✗ Movie not found for code: {code}")
                return False
            
            # Test login stats if login manager available
            if login_manager:
                print("\nLogin Statistics:")
                stats = login_manager.get_login_stats()
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            return True
            
    except Exception as e:
        print(f"✗ JavDB scraper test failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main function for JavDB testing."""
    parser = argparse.ArgumentParser(description='Test JavDB scraper functionality')
    parser.add_argument(
        'code',
        type=str,
        help='Movie code to search for (e.g., ABC-123)'
    )
    parser.add_argument(
        '--username', '-u',
        type=str,
        help='JavDB username for login'
    )
    parser.add_argument(
        '--password', '-p',
        type=str,
        help='JavDB password for login'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in non-headless mode'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    print("JavDB Scraper Test")
    print("=" * 30)
    
    # Validate inputs
    if (args.username and not args.password) or (args.password and not args.username):
        print("❌ Both username and password must be provided for login")
        return 1
    
    # Warning about credentials
    if args.username and not args.verbose:
        print("⚠️  This test will use real JavDB credentials.")
        print("   Make sure you trust this environment.")
        print()
    
    headless = not args.no_headless
    
    success = asyncio.run(test_javdb_scraper(
        code=args.code,
        username=args.username,
        password=args.password,
        headless=headless,
        verbose=args.verbose
    ))
    
    print("\n" + "=" * 30)
    if success:
        print("🎉 JavDB scraper test completed successfully!")
        return 0
    else:
        print("❌ JavDB scraper test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())