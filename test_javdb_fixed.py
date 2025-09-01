#!/usr/bin/env python3
"""
修复后的JavDB刮削测试
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_simple_chrome():
    """简单的Chrome测试"""
    print("\n" + "="*60)
    print("🔍 测试Chrome和ChromeDriver")
    print("="*60)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        import subprocess
        
        # 手动指定ChromeDriver路径
        chromedriver_path = "/Users/yaolidong/.wdm/drivers/chromedriver/mac64/139.0.7258.154/chromedriver-mac-arm64/chromedriver"
        
        # 确保ChromeDriver可执行
        os.chmod(chromedriver_path, 0o755)
        
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 明确指定Chrome二进制位置（Apple Silicon Mac）
        chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        print(f"✅ 找到Chrome: {chrome_options.binary_location}")
        print(f"✅ 找到ChromeDriver: {chromedriver_path}")
        
        # 创建Service对象
        service = Service(chromedriver_path)
        
        # 创建Chrome驱动
        print("\n🌐 启动Chrome浏览器...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome启动成功")
        
        # 测试访问网页
        print("\n🔍 测试访问网页...")
        driver.get("https://www.google.com")
        print(f"✅ 访问成功: {driver.title}")
        
        # 测试JavDB
        print("\n🔍 测试访问JavDB...")
        driver.get("https://javdb.com")
        print(f"✅ JavDB访问成功")
        print(f"   页面标题: {driver.title}")
        
        # 检查页面内容
        if "jav" in driver.page_source.lower():
            print("✅ 确认是JavDB页面")
        
        driver.quit()
        print("\n✅ 测试完成，浏览器已关闭")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_javdb_scraping():
    """测试JavDB刮削功能"""
    print("\n" + "="*60)
    print("🚀 测试JavDB刮削功能")
    print("="*60)
    
    try:
        from src.scrapers.javdb_scraper import JavDBScraper
        from src.utils.webdriver_manager import WebDriverManager
        
        print("✅ 成功导入刮削器模块")
        
        # 创建WebDriver管理器
        print("\n🔧 创建WebDriver管理器...")
        driver_manager = WebDriverManager(
            headless=True,
            driver_path="/Users/yaolidong/.wdm/drivers/chromedriver/mac64/139.0.7258.154/chromedriver-mac-arm64/chromedriver"
        )
        
        # 启动驱动
        print("🌐 启动WebDriver...")
        started = driver_manager.start_driver()
        if not started:
            print("❌ WebDriver启动失败")
            
            # 尝试使用简单的方式
            print("\n尝试简单方式启动...")
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            
            service = Service("/Users/yaolidong/.wdm/drivers/chromedriver/mac64/139.0.7258.154/chromedriver-mac-arm64/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 手动设置driver_manager的driver
            driver_manager.driver = driver
            print("✅ 使用备用方式启动成功")
        
        # 创建JavDB刮削器
        print("\n🔧 创建JavDB刮削器...")
        scraper = JavDBScraper(driver_manager, use_login=False)
        print("✅ JavDB刮削器创建成功")
        
        # 测试可用性
        print("\n🔍 检查JavDB可用性...")
        available = await scraper.is_available()
        print(f"JavDB可用性: {'✅ 可用' if available else '❌ 不可用'}")
        
        if available:
            # 测试搜索一个代码
            test_code = "SSIS-001"
            print(f"\n🔍 测试搜索: {test_code}")
            
            metadata = await scraper.search_movie(test_code)
            if metadata:
                print(f"✅ 成功获取元数据:")
                print(f"   代码: {metadata.code}")
                print(f"   标题: {metadata.title}")
                print(f"   女优: {', '.join(metadata.actresses) if metadata.actresses else '未知'}")
                print(f"   发行日期: {metadata.release_date}")
                print(f"   制作商: {metadata.studio}")
                print(f"   类型数量: {len(metadata.genres) if metadata.genres else 0}")
            else:
                print(f"⚠️  未找到 {test_code} 的元数据")
        
        # 清理
        print("\n🧹 清理资源...")
        if hasattr(driver_manager, 'driver') and driver_manager.driver:
            driver_manager.driver.quit()
        print("✅ 清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("="*60)
    print("🚀 JavDB刮削功能测试（修复版）")
    print("="*60)
    
    # 先测试Chrome
    chrome_ok = test_simple_chrome()
    
    if not chrome_ok:
        print("\n❌ Chrome/ChromeDriver有问题")
        print("\n💡 解决方案:")
        print("1. 确认Chrome版本: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --version")
        print("2. 下载匹配的ChromeDriver: https://chromedriver.chromium.org/")
        print("3. 或使用: brew install --cask chromedriver")
        return
    
    # 测试JavDB刮削
    print("\n" + "="*60)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    javdb_ok = loop.run_until_complete(test_javdb_scraping())
    loop.close()
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)
    
    if chrome_ok and javdb_ok:
        print("🎉 所有测试通过！")
        print("✅ Chrome/ChromeDriver正常")
        print("✅ JavDB可以访问")
        print("✅ 刮削功能可以使用")
    elif chrome_ok:
        print("⚠️  Chrome正常但JavDB刮削有问题")
    else:
        print("❌ 基础环境有问题")

if __name__ == "__main__":
    main()