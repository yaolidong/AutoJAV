#!/usr/bin/env python3
"""
打开JavDB浏览器并保持会话
用户可以在VNC中手动登录
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys
import json
from datetime import datetime
from pathlib import Path

def open_javdb_browser():
    """打开JavDB供手动登录"""
    
    print("=" * 60)
    print("🔐 JavDB 浏览器控制")
    print("=" * 60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    selenium_url = 'http://localhost:4444/wd/hub'
    
    try:
        print("正在启动浏览器...")
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        
        print("✅ 浏览器已启动!")
        
        # 访问JavDB
        print("\n正在访问JavDB...")
        driver.get("https://javdb.com")
        time.sleep(2)
        
        print(f"当前页面: {driver.title}")
        print(f"URL: {driver.current_url}")
        
        print("\n" + "=" * 60)
        print("📺 查看浏览器：")
        print("   访问: http://localhost:7900")
        print("   密码: secret")
        print("\n💡 操作说明：")
        print("   1. 在VNC中手动登录JavDB")
        print("   2. 登录成功后，运行 save_cookies.py 保存登录状态")
        print("   3. 或者在Web界面点击'保存Cookies'按钮")
        print("=" * 60)
        
        print("\n⏸️  浏览器保持开启中... (按Ctrl+C关闭)")
        
        # 每30秒检查并保存一次cookies
        while True:
            try:
                time.sleep(30)
                
                # 获取cookies
                cookies = driver.get_cookies()
                has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)
                
                if has_session:
                    # 自动保存cookies
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
                    
                    print(f"\n✅ 检测到登录会话，Cookies已自动保存!")
                    print(f"   保存位置: {cookie_file}")
                else:
                    print(".", end="", flush=True)  # 显示等待中
                    
            except KeyboardInterrupt:
                print("\n\n正在关闭浏览器...")
                break
            except Exception as e:
                print(f"\n检查时出错: {e}")
                continue
        
        driver.quit()
        print("✅ 浏览器已关闭")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(open_javdb_browser())