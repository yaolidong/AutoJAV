#!/usr/bin/env python3
"""
使用Chrome DevTools Protocol查看和控制浏览器
这是真正能看到浏览器界面的方法
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys

def open_with_devtools():
    """打开带调试端口的Chrome"""
    
    print("=" * 60)
    print("🔧 Chrome DevTools 浏览器控制")
    print("=" * 60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 启用远程调试端口 - 这是关键！
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--remote-debugging-address=0.0.0.0')
    
    # 使用主应用的Selenium Grid
    selenium_url = 'http://localhost:4444/wd/hub'
    
    try:
        print(f"启动Chrome with DevTools...")
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        
        print("✅ Chrome已启动！")
        
        # 访问测试页面
        driver.get("https://www.google.com")
        
        print("\n" + "=" * 60)
        print("🎉 现在你可以通过Chrome DevTools查看浏览器！")
        print("\n访问方法：")
        print("1. 打开Chrome浏览器")
        print("2. 访问: chrome://inspect")
        print("3. 点击 'Configure' 添加: localhost:9222")
        print("4. 你会看到远程浏览器会话")
        print("5. 点击 'inspect' 查看和控制")
        print("=" * 60)
        
        print("\n按Ctrl+C关闭...")
        
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            pass
        
        driver.quit()
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(open_with_devtools())