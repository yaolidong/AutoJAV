#!/usr/bin/env python3
"""
创建可在VNC中显示的浏览器会话
关键是确保Chrome不使用headless模式
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import sys

def create_visible_browser():
    """创建可在VNC中看到的浏览器"""
    
    print("=" * 60)
    print("创建可见浏览器会话 (VNC)")
    print("=" * 60)
    
    # Chrome选项配置
    options = Options()
    
    # 重要：确保不使用headless模式
    # 不要添加 --headless 参数！
    
    # 基本设置
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')  # 对于某些环境有帮助
    
    # 窗口设置
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--window-position=0,0')
    options.add_argument('--start-maximized')  # 最大化窗口
    
    # 禁用一些可能导致问题的功能
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    
    # 用户代理
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # 重要：设置display参数，确保Chrome使用正确的显示
    options.add_argument('--display=:99.0')
    
    # Selenium Grid URL
    selenium_grid_url = 'http://localhost:4444/wd/hub'
    
    try:
        print(f"连接到Selenium Grid: {selenium_grid_url}")
        
        # 创建远程WebDriver
        driver = webdriver.Remote(
            command_executor=selenium_grid_url,
            options=options
        )
        
        print("✅ 浏览器会话已创建!")
        
        # 访问一个页面以确认工作
        print("\n访问测试页面...")
        driver.get("https://www.google.com")
        
        print(f"✅ 成功访问: {driver.title}")
        
        print("\n" + "=" * 60)
        print("🎉 浏览器应该在VNC中可见了！")
        print("\n📺 查看步骤：")
        print("1. 打开浏览器访问: http://localhost:7900")
        print("2. 输入密码: secret")
        print("3. 点击 'Connect'")
        print("4. 你应该能看到Chrome浏览器窗口")
        print("\n如果看不到浏览器，可能的原因：")
        print("- Chrome运行在headless模式")
        print("- DISPLAY设置不正确")
        print("- VNC服务配置问题")
        print("=" * 60)
        
        print("\n保持会话开启中... (按Ctrl+C退出)")
        
        # 保持会话
        try:
            while True:
                time.sleep(10)
                # 定期检查连接
                try:
                    _ = driver.current_url
                except:
                    print("浏览器连接已断开")
                    break
        except KeyboardInterrupt:
            print("\n正在关闭...")
        
        driver.quit()
        print("✅ 浏览器已关闭")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(create_visible_browser())