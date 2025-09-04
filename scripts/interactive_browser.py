#!/usr/bin/env python3
"""
交互式控制Selenium Grid浏览器
在Python交互模式下使用，可以手动输入命令控制浏览器
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def create_browser():
    """创建浏览器实例"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # 连接到Selenium Grid
    driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=options
    )
    
    print("✅ 浏览器已创建!")
    print("\n使用方法:")
    print("  driver.get('https://www.google.com')  # 访问网站")
    print("  driver.title                          # 查看标题")
    print("  driver.current_url                    # 查看当前URL")
    print("  driver.save_screenshot('test.png')    # 截图")
    print("  driver.quit()                         # 关闭浏览器")
    print("\n📺 VNC查看: http://localhost:7900 (密码: secret)")
    
    return driver

# 如果直接运行脚本
if __name__ == "__main__":
    print("=" * 60)
    print("Selenium Grid 浏览器交互控制")
    print("=" * 60)
    
    # 创建浏览器
    driver = create_browser()
    
    # 访问Google作为测试
    driver.get('https://www.google.com')
    print(f"\n当前页面: {driver.title}")
    
    print("\n现在你可以：")
    print("1. 打开 http://localhost:7900 查看浏览器")
    print("2. 在Python控制台输入命令控制浏览器")
    print("\n示例命令：")
    print("  driver.get('https://javdb.com')")
    print("  driver.find_element('name', 'q').send_keys('test')")
    
    # 进入交互模式
    import code
    code.interact(local=locals())