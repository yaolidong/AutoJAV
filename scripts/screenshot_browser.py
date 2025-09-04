#!/usr/bin/env python3
"""
通过截图查看浏览器状态
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os

def browser_with_screenshots():
    """创建浏览器并定期截图"""
    
    print("=" * 60)
    print("📸 截图浏览器控制")
    print("=" * 60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # 创建截图目录
    screenshot_dir = "/Users/yaolidong/Documents/GitHub/AutoJAV/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    
    selenium_url = 'http://localhost:4444/wd/hub'
    
    try:
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        
        print("✅ 浏览器已启动！")
        
        # 访问网站并截图
        sites = [
            ("https://www.google.com", "google.png"),
            ("https://javdb.com", "javdb.png"),
        ]
        
        for url, filename in sites:
            print(f"\n访问: {url}")
            driver.get(url)
            time.sleep(3)  # 等待加载
            
            screenshot_path = os.path.join(screenshot_dir, filename)
            driver.save_screenshot(screenshot_path)
            print(f"✅ 截图已保存: {screenshot_path}")
        
        print("\n" + "=" * 60)
        print("📁 截图已保存到: " + screenshot_dir)
        print("你可以查看这些截图来了解浏览器状态")
        print("=" * 60)
        
        # 进入交互模式
        print("\n进入交互模式，可用命令：")
        print("  driver.get('url')  # 访问网址")
        print("  driver.save_screenshot('file.png')  # 截图")
        print("  driver.quit()  # 退出")
        
        import code
        code.interact(local={'driver': driver})
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    browser_with_screenshots()