#!/usr/bin/env python3
"""
实际的JavDB刮削测试
测试JavDB是否可以真正刮削数据
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_real_javdb_scraping():
    """测试实际的JavDB刮削功能"""
    print("\n" + "="*60)
    print("🚀 开始实际的JavDB刮削测试")
    print("="*60)
    
    try:
        from src.scrapers.javdb_scraper import JavDBScraper
        from src.utils.webdriver_manager import WebDriverManager
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("\n✅ 成功导入所有必要的模块")
        
        # 配置Chrome选项
        print("\n🔧 配置Chrome选项...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 尝试创建Chrome驱动
        print("\n🌐 尝试启动Chrome浏览器...")
        try:
            # 自动下载和管理ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Chrome浏览器启动成功")
            
            # 测试访问JavDB
            print("\n🔍 测试访问JavDB网站...")
            driver.get("https://javdb.com")
            print(f"✅ 成功访问JavDB")
            print(f"   页面标题: {driver.title}")
            print(f"   当前URL: {driver.current_url}")
            
            # 获取页面源码的一部分
            page_source = driver.page_source[:500]
            if "javdb" in page_source.lower() or "jav" in page_source.lower():
                print("✅ 页面内容确认是JavDB")
            
            driver.quit()
            print("✅ 浏览器正常关闭")
            
        except Exception as e:
            print(f"❌ Chrome启动失败: {e}")
            print("\n💡 解决方案:")
            print("1. 确保Chrome浏览器已安装")
            print("2. 安装ChromeDriver: brew install chromedriver")
            print("3. 或让webdriver-manager自动管理")
            return False
        
        # 创建WebDriver管理器
        print("\n🔧 创建WebDriver管理器...")
        driver_manager = WebDriverManager(headless=True)
        
        # 启动驱动
        print("🌐 启动WebDriver...")
        if driver_manager.start_driver():
            print("✅ WebDriver启动成功")
        else:
            print("❌ WebDriver启动失败")
            return False
        
        # 创建JavDB刮削器
        print("\n🔧 创建JavDB刮削器...")
        scraper = JavDBScraper(driver_manager, use_login=False)
        print("✅ JavDB刮削器创建成功")
        
        # 测试可用性
        print("\n🔍 检查JavDB可用性...")
        available = await scraper.is_available()
        if available:
            print("✅ JavDB可用")
        else:
            print("❌ JavDB不可用")
            driver_manager.quit()
            return False
        
        # 测试搜索功能
        test_codes = ["SSIS-001", "IPX-123", "STARS-456"]
        print(f"\n🔍 测试搜索功能，测试代码: {test_codes}")
        
        for code in test_codes:
            print(f"\n搜索 {code}...")
            try:
                metadata = await scraper.search_movie(code)
                if metadata:
                    print(f"✅ 找到 {code} 的元数据:")
                    print(f"   标题: {metadata.title}")
                    print(f"   女优: {', '.join(metadata.actresses) if metadata.actresses else '未知'}")
                    print(f"   发行日期: {metadata.release_date}")
                    print(f"   片长: {metadata.duration} 分钟")
                    print(f"   制作商: {metadata.studio}")
                    print(f"   类型: {', '.join(metadata.genres[:5]) if metadata.genres else '未知'}")
                    if metadata.cover_url:
                        print(f"   封面: {metadata.cover_url[:50]}...")
                else:
                    print(f"⚠️  未找到 {code} 的元数据")
            except Exception as e:
                print(f"❌ 搜索 {code} 时出错: {e}")
            
            # 避免请求过快
            await asyncio.sleep(3)
        
        # 清理
        print("\n🧹 清理资源...")
        driver_manager.quit()
        print("✅ 资源清理完成")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\n💡 请确保已安装所有依赖:")
        print("   pip install selenium webdriver-manager beautifulsoup4")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_selenium():
    """简单的Selenium测试"""
    print("\n" + "="*60)
    print("🔍 简单Selenium测试")
    print("="*60)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        print("尝试创建Chrome驱动...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("访问测试页面...")
        driver.get("https://www.google.com")
        print(f"✅ 页面标题: {driver.title}")
        
        driver.quit()
        print("✅ Selenium测试成功")
        return True
        
    except Exception as e:
        print(f"❌ Selenium测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("="*60)
    print("🚀 JavDB 实际刮削功能测试")
    print("="*60)
    
    # 运行异步测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 先测试Selenium
    print("\n第一步：测试Selenium是否正常工作")
    selenium_ok = loop.run_until_complete(test_simple_selenium())
    
    if not selenium_ok:
        print("\n❌ Selenium不能正常工作，请先解决浏览器问题")
        print("\n💡 解决方案:")
        print("1. 确保Chrome已安装: /Applications/Google Chrome.app 应该存在")
        print("2. 安装/更新ChromeDriver: brew install --cask chromedriver")
        print("3. 如果有安全提示: xattr -d com.apple.quarantine /usr/local/bin/chromedriver")
        loop.close()
        return
    
    # 测试JavDB刮削
    print("\n第二步：测试JavDB刮削功能")
    javdb_ok = loop.run_until_complete(test_real_javdb_scraping())
    
    loop.close()
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)
    
    if selenium_ok and javdb_ok:
        print("🎉 所有测试通过！JavDB刮削功能正常工作")
    elif selenium_ok:
        print("⚠️  Selenium正常但JavDB刮削失败")
        print("可能原因：")
        print("- 网络连接问题")
        print("- JavDB网站结构变化")
        print("- 需要代理访问")
    else:
        print("❌ 基础环境有问题，请先修复")
    
    print("\n📝 注意事项:")
    print("1. JavDB可能需要代理才能访问")
    print("2. 频繁请求可能触发反爬保护")
    print("3. 建议添加登录功能以获得更好的访问权限")
    print("4. 实际使用时建议增加请求间隔")

if __name__ == "__main__":
    main()