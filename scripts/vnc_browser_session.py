#!/usr/bin/env python3
"""
在VNC中打开一个浏览器会话
用户可以在VNC中手动操作浏览器
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys

def start_vnc_browser():
    """启动浏览器会话供VNC查看和操作"""
    
    print("=" * 60)
    print("🌐 VNC浏览器会话")
    print("=" * 60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    # 禁用安全功能以便访问更多网站
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    
    selenium_url = 'http://localhost:4444/wd/hub'
    
    try:
        print("正在启动浏览器...")
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        
        print("✅ 浏览器已启动!")
        
        # 先访问一个肯定能访问的页面
        print("\n访问Google...")
        driver.get("https://www.google.com")
        time.sleep(1)
        
        print(f"当前页面: {driver.title}")
        
        print("\n" + "=" * 60)
        print("📺 在VNC中查看和控制浏览器：")
        print("\n1. 打开VNC界面:")
        print("   访问: http://localhost:7900")
        print("   密码: secret")
        print("\n2. 在VNC中你可以：")
        print("   - 手动输入网址访问任何网站")
        print("   - 尝试使用VPN或代理访问被封锁的网站")
        print("   - 完成登录后保存cookies")
        print("\n3. 建议的操作步骤：")
        print("   a) 在地址栏输入: javdb.com")
        print("   b) 如果无法访问，尝试使用代理")
        print("   c) 或者搜索'javdb proxy'寻找镜像站点")
        print("=" * 60)
        
        print("\n⏸️  浏览器会话保持中... (按Ctrl+C关闭)")
        print("提示：每30秒会自动检查并保存cookies")
        
        # 保持会话并定期检查
        import json
        from datetime import datetime
        from pathlib import Path
        
        last_url = ""
        while True:
            try:
                time.sleep(30)
                
                # 检查当前URL
                current_url = driver.current_url
                if current_url != last_url:
                    print(f"\n当前页面: {current_url}")
                    last_url = current_url
                
                # 如果在javdb相关页面，尝试保存cookies
                if 'javdb' in current_url.lower():
                    cookies = driver.get_cookies()
                    if cookies:
                        config_dir = Path("/Users/yaolidong/Documents/GitHub/AutoJAV/config")
                        config_dir.mkdir(exist_ok=True)
                        
                        cookie_file = config_dir / "javdb_cookies.json"
                        cookie_data = {
                            "cookies": cookies,
                            "timestamp": datetime.now().isoformat(),
                            "domain": current_url
                        }
                        
                        with open(cookie_file, 'w') as f:
                            json.dump(cookie_data, f, indent=2)
                        
                        print(f"✅ Cookies已自动保存到: {cookie_file}")
                
            except KeyboardInterrupt:
                print("\n\n正在关闭浏览器...")
                break
            except Exception as e:
                # 忽略错误，继续运行
                pass
        
        driver.quit()
        print("✅ 浏览器已关闭")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(start_vnc_browser())