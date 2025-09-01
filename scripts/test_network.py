#!/usr/bin/env python3
"""
Test script for network and browser functionality.

This script tests the HttpClient and WebDriverManager components.
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.http_client import HttpClient
from src.utils.webdriver_manager import WebDriverManager


async def test_http_client():
    """Test HttpClient functionality."""
    print("Testing HttpClient...")
    
    try:
        async with HttpClient(timeout=10, rate_limit_delay=0.5) as client:
            print("✓ HttpClient created successfully")
            
            # Test GET request
            print("Making GET request to httpbin.org...")
            response = await client.get("https://httpbin.org/get")
            
            if response.status == 200:
                print(f"✓ GET request successful: {response.status}")
                data = await response.json()
                print(f"  User-Agent: {data.get('headers', {}).get('User-Agent', 'N/A')}")
            else:
                print(f"✗ GET request failed: {response.status}")
            
            # Test POST request
            print("Making POST request to httpbin.org...")
            response = await client.post(
                "https://httpbin.org/post",
                json={"test": "data", "timestamp": "2024-01-01"}
            )
            
            if response.status == 200:
                print(f"✓ POST request successful: {response.status}")
                data = await response.json()
                sent_data = data.get('json', {})
                print(f"  Sent data: {sent_data}")
            else:
                print(f"✗ POST request failed: {response.status}")
            
            # Get client stats
            stats = client.get_stats()
            print(f"✓ Client stats: {stats['request_count']} requests made")
            
    except Exception as e:
        print(f"✗ HttpClient test failed: {e}")
        return False
    
    return True


def test_webdriver_manager(headless=True):
    """Test WebDriverManager functionality."""
    print(f"Testing WebDriverManager (headless={headless})...")
    
    try:
        with WebDriverManager(headless=headless, timeout=10) as manager:
            print("✓ WebDriverManager created successfully")
            
            # Test navigation
            print("Navigating to example.com...")
            success = manager.get_page("https://example.com")
            
            if success:
                print("✓ Page navigation successful")
                
                # Get page title
                title = manager.get_text("title")
                print(f"  Page title: {title or 'N/A'}")
                
                # Get current URL
                current_url = manager.get_current_url()
                print(f"  Current URL: {current_url}")
                
                # Test element finding
                h1_element = manager.find_element("h1")
                if h1_element:
                    h1_text = manager.get_text("h1")
                    print(f"  H1 text: {h1_text}")
                else:
                    print("  No H1 element found")
                
                # Test JavaScript execution
                page_height = manager.execute_script("return document.body.scrollHeight;")
                print(f"  Page height: {page_height}px")
                
                # Test screenshot (only in non-headless mode for visibility)
                if not headless:
                    screenshot_path = "/tmp/test_screenshot.png"
                    if manager.take_screenshot(screenshot_path):
                        print(f"✓ Screenshot saved: {screenshot_path}")
                    else:
                        print("✗ Screenshot failed")
                
            else:
                print("✗ Page navigation failed")
                return False
            
            # Test driver alive check
            if manager.is_driver_alive():
                print("✓ WebDriver is alive and responsive")
            else:
                print("✗ WebDriver is not responsive")
                return False
            
    except Exception as e:
        print(f"✗ WebDriverManager test failed: {e}")
        return False
    
    return True


async def main():
    """Main function for network testing."""
    parser = argparse.ArgumentParser(description='Test network and browser components')
    parser.add_argument(
        '--skip-http',
        action='store_true',
        help='Skip HTTP client tests'
    )
    parser.add_argument(
        '--skip-browser',
        action='store_true',
        help='Skip browser tests'
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
    
    print("Network and Browser Component Tests")
    print("=" * 40)
    
    success_count = 0
    total_tests = 0
    
    # Test HTTP Client
    if not args.skip_http:
        total_tests += 1
        print("\n1. HTTP Client Test")
        print("-" * 20)
        
        if await test_http_client():
            success_count += 1
            print("✓ HTTP Client test PASSED")
        else:
            print("✗ HTTP Client test FAILED")
    
    # Test WebDriver Manager
    if not args.skip_browser:
        total_tests += 1
        print("\n2. WebDriver Manager Test")
        print("-" * 25)
        
        headless = not args.no_headless
        if test_webdriver_manager(headless=headless):
            success_count += 1
            print("✓ WebDriver Manager test PASSED")
        else:
            print("✗ WebDriver Manager test FAILED")
    
    # Summary
    print("\n" + "=" * 40)
    print(f"Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))