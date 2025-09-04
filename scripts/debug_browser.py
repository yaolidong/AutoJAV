#!/usr/bin/env python3
"""
使用独立的调试Selenium容器打开浏览器
这个容器专门用于手动调试和查看浏览器
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys

def open_debug_browser(url="https://www.google.com"):
    """在调试容器中打开浏览器"""
    
    print("=" * 60)
    print("🔧 Selenium调试浏览器控制")
    print("=" * 60)
    
    # Chrome选项
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # 使用主应用的Selenium Grid端口4444
    selenium_grid_url = 'http://localhost:4444/wd/hub'
    
    try:
        print(f"连接到Selenium Grid: {selenium_grid_url}")
        driver = webdriver.Remote(
            command_executor=selenium_grid_url,
            options=options
        )
        
        print("✅ 成功连接到Selenium Grid!")
        
        print(f"\n访问: {url}")
        driver.get(url)
        print(f"✅ 页面标题: {driver.title}")
        
        print("\n" + "=" * 60)
        print("🎉 浏览器已打开！")
        print("\n📺 查看浏览器的两种方法：")
        print("\n方法1 - Web VNC (推荐):")
        print("  访问: http://localhost:7900")
        print("  密码: secret")
        print("\n方法2 - VNC客户端:")
        print("  地址: localhost:5900")
        print("  密码: secret")
        print("=" * 60)
        
        print("\n可用命令:")
        print("  driver.get('https://javdb.com')     # 访问JavDB")
        print("  driver.get('https://javlibrary.com') # 访问JavLibrary")
        print("  driver.save_screenshot('test.png')   # 截图")
        print("  driver.quit()                        # 关闭浏览器")
        
        print("\n⏸️  浏览器保持开启... (按Ctrl+C关闭)")
        
        # 进入交互模式
        import code
        code.interact(local={'driver': driver})
        
    except KeyboardInterrupt:
        print("\n正在关闭...")
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请确保容器正在运行:")
        print("  docker compose up -d")
        return 1
    finally:
        if 'driver' in locals():
            try:
                driver.quit()
                print("✅ 浏览器已关闭")
            except:
                pass
    
    return 0

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
    sys.exit(open_debug_browser(url))