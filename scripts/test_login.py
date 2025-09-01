#!/usr/bin/env python3
"""
Test script for login functionality.

This script tests the LoginManager with a real website.
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.webdriver_manager import WebDriverManager
from src.utils.login_manager import LoginManager


def test_login_manager(username: str, password: str, login_url: str, headless: bool = True):
    """
    Test LoginManager functionality.
    
    Args:
        username: Login username
        password: Login password
        login_url: URL of the login page
        headless: Run browser in headless mode
    """
    print(f"Testing LoginManager with {login_url}")
    print(f"Username: {username}")
    print(f"Headless mode: {headless}")
    print("-" * 40)
    
    try:
        with WebDriverManager(headless=headless, timeout=30) as driver_manager:
            print("✓ WebDriver started successfully")
            
            # Create login manager
            login_manager = LoginManager(
                username=username,
                password=password,
                driver_manager=driver_manager,
                cookies_file=f"cookies_{username}.json"
            )
            
            print("✓ LoginManager created successfully")
            
            # Test login
            print(f"Attempting login to {login_url}...")
            
            async def test_login():
                success = await login_manager.login(login_url)
                return success
            
            login_success = asyncio.run(test_login())
            
            if login_success:
                print("✓ Login successful!")
                
                # Test login status check
                async def check_status():
                    return await login_manager.is_logged_in()
                
                is_logged_in = asyncio.run(check_status())
                print(f"✓ Login status check: {'Logged in' if is_logged_in else 'Not logged in'}")
                
                # Test session refresh
                print("Testing session refresh...")
                
                async def refresh_session():
                    return await login_manager.refresh_session()
                
                refresh_success = asyncio.run(refresh_session())
                print(f"✓ Session refresh: {'Success' if refresh_success else 'Failed'}")
                
                # Show login stats
                stats = login_manager.get_login_stats()
                print("\nLogin Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                
            else:
                print("✗ Login failed!")
                
                # Show login stats for debugging
                stats = login_manager.get_login_stats()
                print("\nLogin Statistics (for debugging):")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                
                return False
            
            # Test cookie functionality
            print("\nTesting cookie functionality...")
            
            async def test_cookies():
                # Save cookies
                save_success = await login_manager.save_cookies()
                print(f"✓ Save cookies: {'Success' if save_success else 'Failed'}")
                
                # Clear cookies from manager
                login_manager.clear_cookies()
                print("✓ Cookies cleared from manager")
                
                # Load cookies back
                load_success = await login_manager.load_cookies()
                print(f"✓ Load cookies: {'Success' if load_success else 'Failed'}")
                
                return save_success and load_success
            
            cookie_test = asyncio.run(test_cookies())
            
            if cookie_test:
                print("✓ Cookie functionality working correctly")
            else:
                print("✗ Cookie functionality failed")
            
            return login_success and cookie_test
            
    except Exception as e:
        print(f"✗ LoginManager test failed: {e}")
        return False


def main():
    """Main function for login testing."""
    parser = argparse.ArgumentParser(description='Test login functionality')
    parser.add_argument(
        '--username', '-u',
        type=str,
        required=True,
        help='Login username'
    )
    parser.add_argument(
        '--password', '-p',
        type=str,
        required=True,
        help='Login password'
    )
    parser.add_argument(
        '--url',
        type=str,
        default='https://httpbin.org/forms/post',  # Default test URL
        help='Login page URL (default: httpbin test form)'
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
    
    print("Login Manager Test")
    print("=" * 30)
    
    # Warning about credentials
    if not args.verbose:
        print("⚠️  This test will use real credentials. Make sure you trust this environment.")
        print("   Use --verbose flag to see more details about what's being tested.")
        print()
    
    headless = not args.no_headless
    
    success = test_login_manager(
        username=args.username,
        password=args.password,
        login_url=args.url,
        headless=headless
    )
    
    print("\n" + "=" * 30)
    if success:
        print("🎉 Login test completed successfully!")
        return 0
    else:
        print("❌ Login test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())