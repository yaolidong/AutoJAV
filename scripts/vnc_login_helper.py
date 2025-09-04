#!/usr/bin/env python3
"""
VNC Login Helper - 在VNC会话中自动打开浏览器并导航到JavDB登录页面
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys

def open_javdb_in_vnc():
    """在VNC会话中打开浏览器并导航到JavDB登录页面"""
    try:
        # 连接到Selenium Grid
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 连接到Selenium Grid
        driver = webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            options=options
        )
        
        print("✅ 成功连接到Selenium Grid")
        print("📌 浏览器已在VNC会话中打开")
        
        # 导航到JavDB登录页面
        driver.get('https://javdb.com/login')
        print("🌐 已导航到JavDB登录页面")
        print("\n请在VNC窗口中完成以下步骤：")
        print("1. 输入您的JavDB用户名和密码")
        print("2. 完成验证码（如果有）")
        print("3. 点击登录按钮")
        print("\n登录成功后，按Ctrl+C退出此脚本...")
        
        # 保持浏览器打开
        while True:
            time.sleep(1)
            # 检查是否已登录（通过查找登出链接）
            try:
                if driver.find_elements("css selector", "a[href*='/logout']"):
                    print("\n✅ 检测到已登录成功！")
                    break
            except:
                pass
                
    except KeyboardInterrupt:
        print("\n⏹ 用户中断")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        if 'driver' in locals():
            print("正在关闭浏览器...")
            driver.quit()

if __name__ == "__main__":
    print("=" * 60)
    print("JavDB VNC登录助手")
    print("=" * 60)
    print("\n请确保：")
    print("1. 您已经打开了 http://localhost:7900 (noVNC)")
    print("2. 输入密码 'secret' 并连接到VNC会话")
    print("3. 您可以看到Selenium Grid的桌面")
    print("\n准备好后按Enter继续...")
    input()
    
    open_javdb_in_vnc()