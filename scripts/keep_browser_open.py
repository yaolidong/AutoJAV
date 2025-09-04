#!/usr/bin/env python3
"""
在Selenium Grid中打开浏览器并保持会话，以便通过VNC查看
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import signal
import sys

# 全局变量存储driver
driver = None

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    global driver
    print('\n正在关闭浏览器...')
    if driver:
        try:
            driver.quit()
        except:
            pass
    sys.exit(0)

def keep_browser_open():
    """打开浏览器并保持会话"""
    global driver
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("Selenium Grid 浏览器会话管理器")
    print("=" * 60)
    
    # 配置Chrome选项
    options = Options()
    # 重要：不使用headless模式，这样才能在VNC中看到
    # options.add_argument('--headless')  # 不要启用这个
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # 设置User Agent
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Selenium Grid地址
    selenium_grid_url = 'http://localhost:4444/wd/hub'
    
    try:
        print(f"1. 连接到Selenium Grid: {selenium_grid_url}")
        driver = webdriver.Remote(
            command_executor=selenium_grid_url,
            options=options
        )
        print("   ✅ 成功连接!")
        
        # 打开一个初始页面
        print("\n2. 打开初始页面...")
        driver.get("https://www.google.com")
        print(f"   ✅ 当前页面: {driver.title}")
        
        print("\n" + "=" * 60)
        print("🎉 浏览器已启动！")
        print("\n📺 查看浏览器的方法：")
        print("   1. 打开浏览器访问: http://localhost:7900")
        print("   2. 输入密码: secret")
        print("   3. 点击 'Connect' 按钮")
        print("   4. 现在你应该能看到Chrome浏览器界面了！")
        print("\n💡 提示：")
        print("   - 你可以在VNC中直接操作浏览器")
        print("   - 可以输入网址、点击链接、填写表单等")
        print("   - 按F12可以打开开发者工具")
        print("   - 按Ctrl+C关闭浏览器并退出程序")
        print("=" * 60)
        print("\n⏸️  浏览器会话保持中... (按Ctrl+C退出)")
        
        # 保持浏览器会话
        while True:
            try:
                # 每30秒检查一次浏览器是否还活着
                current_url = driver.current_url
                time.sleep(30)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n⚠️ 浏览器连接可能已断开: {e}")
                break
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n请检查：")
        print("1. Docker容器是否正在运行:")
        print("   docker compose ps")
        print("2. Selenium Grid是否可访问:")
        print("   curl http://localhost:4444/status")
        print("3. 查看容器日志:")
        print("   docker compose logs av-scraper-web --tail=50")
        return 1
    
    finally:
        if driver:
            try:
                driver.quit()
                print("✅ 浏览器已关闭")
            except:
                pass
    
    return 0

if __name__ == "__main__":
    sys.exit(keep_browser_open())