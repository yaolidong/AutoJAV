#!/usr/bin/env python3
"""
测试刮削功能
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.javdb_scraper import JavDBScraper
from src.scrapers.javlibrary_scraper import JavLibraryScraper
from src.utils.webdriver_manager import WebDriverManager

async def test_scrape(code='MEYD-888'):
    """测试刮削功能"""
    print(f"\n{'='*60}")
    print(f"测试刮削: {code}")
    print(f"{'='*60}")
    
    # Initialize WebDriver Manager
    driver_manager = WebDriverManager()
    
    # Test JavDB
    print("\n1. 测试JavDB刮削器...")
    try:
        javdb = JavDBScraper(driver_manager)
        result = await javdb.scrape(code)
        if result:
            print(f"   ✅ JavDB刮削成功!")
            print(f"   标题: {result.get('title', 'N/A')}")
            print(f"   女优: {', '.join(result.get('actresses', []))}")
        else:
            print(f"   ❌ JavDB刮削失败 - 无结果返回")
    except Exception as e:
        print(f"   ❌ JavDB刮削错误: {e}")
    
    # Test JavLibrary
    print("\n2. 测试JavLibrary刮削器...")
    try:
        javlib = JavLibraryScraper(driver_manager)
        result = await javlib.scrape(code)
        if result:
            print(f"   ✅ JavLibrary刮削成功!")
            print(f"   标题: {result.get('title', 'N/A')}")
            print(f"   女优: {', '.join(result.get('actresses', []))}")
        else:
            print(f"   ❌ JavLibrary刮削失败 - 无结果返回")
    except Exception as e:
        print(f"   ❌ JavLibrary刮削错误: {e}")
    
    # Clean up
    driver_manager.quit()
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else 'MEYD-888'
    asyncio.run(test_scrape(code))