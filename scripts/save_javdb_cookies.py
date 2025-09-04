#!/usr/bin/env python3
"""
从当前Selenium会话中获取并保存JavDB cookies
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
from datetime import datetime
from pathlib import Path
import sys

def save_cookies_from_session():
    """从Selenium会话中获取并保存cookies"""
    try:
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 连接到已有的Selenium会话
        driver = webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            options=options
        )
        
        print("✅ 已连接到Selenium Grid")
        
        # 获取当前页面URL
        current_url = driver.current_url
        print(f"📍 当前页面: {current_url}")
        
        # 检查是否在JavDB域名下
        if 'javdb.com' not in current_url:
            print("⚠️ 当前不在JavDB网站，正在导航...")
            driver.get('https://javdb.com')
        
        # 获取所有cookies
        cookies = driver.get_cookies()
        print(f"🍪 获取到 {len(cookies)} 个cookies")
        
        # 准备保存的数据
        cookie_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "domain": "https://javdb.com"
        }
        
        # 保存到配置目录
        config_dir = Path('/Users/yaolidong/Documents/GitHub/AutoJAV/config')
        cookie_file = config_dir / 'javdb_cookies.json'
        
        with open(cookie_file, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        
        print(f"✅ Cookies已保存到: {cookie_file}")
        
        # 检查是否已登录
        try:
            logout_links = driver.find_elements("css selector", "a[href*='/logout']")
            if logout_links:
                print("✅ 检测到已登录状态")
                
                # 显示用户信息（如果有）
                try:
                    user_info = driver.find_element("css selector", ".user-menu, .avatar, .username")
                    print(f"👤 用户: {user_info.text}")
                except:
                    pass
            else:
                print("⚠️ 未检测到登录状态，请确认是否已登录")
        except:
            pass
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("JavDB Cookie 保存工具")
    print("=" * 60)
    
    if save_cookies_from_session():
        print("\n✅ Cookie保存成功！")
        print("您现在可以使用保存的cookies进行后续操作。")
    else:
        print("\n❌ Cookie保存失败")
        sys.exit(1)