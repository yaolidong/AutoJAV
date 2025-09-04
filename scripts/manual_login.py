#!/usr/bin/env python3
"""
手动登录JavDB的脚本
在VNC中打开浏览器，让用户可以手动登录
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys

def open_browser_for_login():
    """打开浏览器供手动登录"""
    
    print("=" * 60)
    print("🔐 JavDB 手动登录助手")
    print("=" * 60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # 重要：不使用headless模式
    # options.add_argument('--headless')  # 不要添加这个！
    
    selenium_url = 'http://localhost:4444/wd/hub'
    
    try:
        print("正在启动浏览器...")
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        
        print("✅ 浏览器已启动!")
        
        # 直接访问JavDB登录页面
        print("\n正在访问JavDB...")
        driver.get("https://javdb.com")
        time.sleep(2)
        
        # 尝试访问登录页面
        print("导航到登录页面...")
        driver.get("https://javdb.com/login")
        
        print("\n" + "=" * 60)
        print("📺 请按以下步骤操作：")
        print("\n1. 打开VNC查看浏览器：")
        print("   访问: http://localhost:7900")
        print("   密码: secret")
        print("\n2. 在VNC中完成JavDB登录")
        print("\n3. 登录成功后，按Enter键保存Cookies")
        print("=" * 60)
        
        # 等待用户输入
        input("\n⏸️  请在VNC中完成登录，然后按Enter键继续...")
        
        # 获取当前页面URL检查是否登录成功
        current_url = driver.current_url
        print(f"\n当前页面: {current_url}")
        
        # 获取cookies
        cookies = driver.get_cookies()
        print(f"获取到 {len(cookies)} 个cookies")
        
        # 检查是否有登录会话
        has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)
        
        if has_session:
            print("✅ 检测到登录会话！")
            
            # 保存cookies到文件
            import json
            from datetime import datetime
            from pathlib import Path
            
            config_dir = Path("/Users/yaolidong/Documents/GitHub/AutoJAV/config")
            config_dir.mkdir(exist_ok=True)
            
            cookie_file = config_dir / "javdb_cookies.json"
            cookie_data = {
                "cookies": cookies,
                "timestamp": datetime.now().isoformat(),
                "domain": "https://javdb.com"
            }
            
            with open(cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            print(f"✅ Cookies已保存到: {cookie_file}")
            print("\n🎉 登录成功！现在可以使用刮削功能了。")
        else:
            print("⚠️  未检测到登录会话，请确认是否已登录")
            print("提示：可能需要在JavDB页面上点击登录按钮")
        
        # 询问是否保持浏览器开启
        keep_open = input("\n是否保持浏览器开启？(y/n): ").lower() == 'y'
        
        if keep_open:
            print("\n浏览器将保持开启，按Ctrl+C关闭...")
            try:
                while True:
                    time.sleep(10)
            except KeyboardInterrupt:
                print("\n正在关闭浏览器...")
        
        driver.quit()
        print("✅ 浏览器已关闭")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请确保Docker容器正在运行:")
        print("  docker compose ps")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(open_browser_for_login())