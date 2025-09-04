#!/usr/bin/env python3
"""
快速测试Selenium Grid连接和浏览器打开
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys

def quick_test():
    """快速测试Grid连接"""
    print("=" * 50)
    print("Selenium Grid 快速测试")
    print("=" * 50)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    selenium_grid_url = 'http://localhost:4444/wd/hub'
    
    try:
        print(f"1. 连接到 Selenium Grid: {selenium_grid_url}")
        driver = webdriver.Remote(
            command_executor=selenium_grid_url,
            options=options
        )
        print("   ✅ 连接成功!")
        
        print("\n2. 访问 Google.com")
        driver.get("https://www.google.com")
        print(f"   ✅ 页面标题: {driver.title}")
        
        print("\n3. 获取当前URL")
        print(f"   URL: {driver.current_url}")
        
        print("\n" + "=" * 50)
        print("✅ 测试成功!")
        print("\n📺 查看浏览器:")
        print("   访问: http://localhost:7900")
        print("   密码: secret")
        print("=" * 50)
        
        # 立即关闭，不等待
        driver.quit()
        print("\n浏览器已关闭")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n请检查:")
        print("1. Docker容器是否运行: docker compose ps")
        print("2. Selenium Grid是否可访问: curl http://localhost:4444/status")
        return 1

if __name__ == "__main__":
    sys.exit(quick_test())