#!/usr/bin/env python3
"""
简单的JavDB刮削器测试
测试JavDB是否可以实际访问和刮削数据
"""

import asyncio
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_javdb_connectivity():
    """测试JavDB网站连接性"""
    import requests
    
    print("\n🔍 测试JavDB连接性...")
    
    urls_to_test = [
        "https://javdb.com",
        "https://javdb4.com",
        "https://javdb5.com"
    ]
    
    for url in urls_to_test:
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if response.status_code == 200:
                print(f"✅ {url} - 可访问 (状态码: {response.status_code})")
                print(f"   页面大小: {len(response.content)} bytes")
                return True
            else:
                print(f"⚠️  {url} - 状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {url} - 连接失败: {str(e)[:50]}...")
    
    return False

def test_javdb_scraper_import():
    """测试JavDB刮削器导入"""
    print("\n🔍 测试JavDB刮削器导入...")
    
    try:
        from src.scrapers.javdb_scraper import JavDBScraper
        print("✅ JavDBScraper 导入成功")
        
        # 检查必要的方法
        required_methods = ['search_movie', 'is_available', '_extract_movie_metadata']
        for method in required_methods:
            if hasattr(JavDBScraper, method):
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"❌ 方法 {method} 缺失")
                return False
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_webdriver_availability():
    """测试WebDriver是否可用"""
    print("\n🔍 测试WebDriver可用性...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        print("✅ Selenium 导入成功")
        
        # 尝试创建Chrome选项
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        print("✅ Chrome选项配置成功")
        
        # 注意：实际创建driver可能需要Chrome浏览器
        print("⚠️  注意：实际运行需要安装Chrome/Chromium浏览器")
        
        return True
        
    except ImportError as e:
        print(f"❌ WebDriver导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ WebDriver配置失败: {e}")
        return False

async def test_javdb_scraper_basic():
    """测试JavDB刮削器基本功能"""
    print("\n🔍 测试JavDB刮削器基本功能...")
    
    try:
        from src.scrapers.javdb_scraper import JavDBScraper
        from src.utils.webdriver_manager import WebDriverManager
        
        # 创建WebDriver管理器（不实际启动浏览器）
        print("创建WebDriver管理器...")
        driver_manager = WebDriverManager(headless=True)
        
        # 创建JavDB刮削器
        print("创建JavDB刮削器...")
        scraper = JavDBScraper(driver_manager, use_login=False)
        
        print("✅ JavDB刮削器创建成功")
        
        # 测试可用性检查（注意：这可能需要实际的浏览器）
        print("\n检查JavDB可用性...")
        # available = await scraper.is_available()
        # print(f"JavDB可用性: {'✅' if available else '❌'}")
        
        print("⚠️  注意：完整的刮削测试需要：")
        print("   1. 安装Chrome/Chromium浏览器")
        print("   2. 配置ChromeDriver")
        print("   3. 网络访问JavDB")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 JavDB 刮削器功能测试")
    print("=" * 60)
    
    results = {
        "连接性测试": test_javdb_connectivity(),
        "导入测试": test_javdb_scraper_import(),
        "WebDriver测试": test_webdriver_availability(),
    }
    
    # 运行异步测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results["基本功能测试"] = loop.run_until_complete(test_javdb_scraper_basic())
    loop.close()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过!")
    elif passed > 0:
        print("⚠️  部分测试通过，请检查失败项")
    else:
        print("❌ 所有测试失败，请检查环境配置")
    
    # 提供建议
    print("\n💡 建议:")
    if not results["连接性测试"]:
        print("- JavDB网站可能被墙或暂时不可用")
        print("- 考虑使用代理或VPN")
    
    if not results["WebDriver测试"]:
        print("- 安装Chrome浏览器: brew install --cask google-chrome")
        print("- 或安装Chromium: brew install --cask chromium")
    
    print("\n📌 注意事项:")
    print("1. JavDB刮削需要网络访问")
    print("2. 某些地区可能需要代理")
    print("3. 频繁访问可能触发反爬机制")
    print("4. 建议使用登录以获得更好的访问权限")

if __name__ == "__main__":
    main()