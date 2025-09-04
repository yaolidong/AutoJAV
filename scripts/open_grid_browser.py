#!/usr/bin/env python3
"""
手动打开和控制Selenium Grid中的浏览器
使用这个脚本可以在Selenium Grid中创建一个浏览器会话，并通过VNC查看
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def open_grid_browser(url="https://www.google.com", keep_open=True):
    """
    在Selenium Grid中打开浏览器
    
    Args:
        url: 要访问的URL
        keep_open: 是否保持浏览器开启
    """
    # 配置Chrome选项
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 不使用headless模式，以便在VNC中看到
    # options.add_argument('--headless')
    
    # User agent
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    
    # 连接到Selenium Grid
    selenium_grid_url = 'http://localhost:4444/wd/hub'
    
    print(f"连接到Selenium Grid: {selenium_grid_url}")
    print("=" * 50)
    
    try:
        # 创建远程WebDriver连接
        driver = webdriver.Remote(
            command_executor=selenium_grid_url,
            options=options
        )
        
        print(f"✅ 成功连接到Selenium Grid!")
        print(f"📍 正在访问: {url}")
        print("=" * 50)
        
        # 访问指定的URL
        driver.get(url)
        
        print(f"✅ 成功打开页面: {driver.title}")
        print("=" * 50)
        print("\n🖥️  查看浏览器的方法:")
        print("1. 打开浏览器访问: http://localhost:7900")
        print("2. 输入密码: secret")
        print("3. 点击 'Connect' 按钮")
        print("4. 你将看到Chrome浏览器界面")
        print("\n📝 控制说明:")
        print("- 你可以在VNC界面中直接操作浏览器")
        print("- 也可以通过修改这个脚本来控制浏览器")
        print("=" * 50)
        
        if keep_open:
            print("\n⏸️  浏览器将保持开启状态...")
            print("按 Ctrl+C 关闭浏览器和退出程序")
            
            try:
                # 保持浏览器开启
                while True:
                    time.sleep(1)
                    # 可以在这里添加自动化操作
            except KeyboardInterrupt:
                print("\n正在关闭浏览器...")
        
        return driver
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请确保:")
        print("1. Docker容器正在运行 (docker compose up)")
        print("2. Selenium Grid在端口4444上可访问")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()
            print("✅ 浏览器已关闭")

def test_javdb_access():
    """
    测试访问JavDB网站
    """
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    
    selenium_grid_url = 'http://localhost:4444/wd/hub'
    
    print("测试访问JavDB...")
    print("=" * 50)
    
    try:
        driver = webdriver.Remote(
            command_executor=selenium_grid_url,
            options=options
        )
        
        print("1. 访问Google测试网络...")
        driver.get("https://www.google.com")
        print(f"   ✅ Google访问成功: {driver.title}")
        
        print("\n2. 尝试访问JavDB...")
        driver.get("https://javdb.com")
        time.sleep(5)  # 等待页面加载
        
        current_url = driver.current_url
        page_title = driver.title
        
        print(f"   当前URL: {current_url}")
        print(f"   页面标题: {page_title}")
        
        if "javdb" in current_url.lower():
            print("   ✅ JavDB访问成功!")
        else:
            print("   ❌ JavDB访问失败，可能被重定向或阻止")
        
        print("\n3. 尝试访问JavLibrary...")
        driver.get("https://www.javlibrary.com")
        time.sleep(5)
        
        current_url = driver.current_url
        page_title = driver.title
        
        print(f"   当前URL: {current_url}")
        print(f"   页面标题: {page_title}")
        
        if "javlibrary" in current_url.lower():
            print("   ✅ JavLibrary访问成功!")
        else:
            print("   ❌ JavLibrary访问失败，可能有Cloudflare保护")
        
        print("=" * 50)
        print("\n📱 在VNC中查看详细情况:")
        print("访问 http://localhost:7900 (密码: secret)")
        
        # 保持浏览器开启30秒以便查看
        print("\n浏览器将在30秒后关闭...")
        time.sleep(30)
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_javdb_access()
        else:
            # 访问指定的URL
            open_grid_browser(sys.argv[1])
    else:
        # 默认打开Google
        open_grid_browser()