#!/usr/bin/env python3
"""
JavDB Login Helper Script
Opens a browser session in Selenium Grid for manual login
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import sys
import json
from datetime import datetime
from pathlib import Path

def help_login_javdb():
    """Help user login to JavDB via VNC"""
    
    print("=" * 60)
    print("🔐 JavDB Login Helper")
    print("=" * 60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    # Disable security for testing
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    
    selenium_url = 'http://localhost:4444/wd/hub'
    
    try:
        print("正在连接Selenium Grid...")
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options
        )
        
        print("✅ 浏览器已启动!")
        print("\n" + "=" * 60)
        print("📺 请按以下步骤操作：")
        print("\n1. 打开VNC查看浏览器:")
        print("   访问: http://localhost:7900")
        print("   密码: secret")
        print("\n2. 由于JavDB被网络限制，请尝试以下方法：")
        print("   a) 使用VPN或代理访问JavDB")
        print("   b) 尝试JavDB镜像站点（搜索'javdb mirror'或'javdb proxy'）")
        print("   c) 使用其他可访问的站点")
        print("\n3. 如果成功访问并登录JavDB：")
        print("   登录后按Enter键保存Cookies")
        print("=" * 60)
        
        # 先尝试访问Google确认浏览器工作
        print("\n正在访问Google测试浏览器...")
        driver.get("https://www.google.com")
        time.sleep(1)
        print(f"当前页面: {driver.title}")
        
        print("\n提示: 在VNC中手动输入JavDB地址或镜像站点地址")
        print("如果需要代理，可以在浏览器中配置")
        
        # 等待用户操作
        input("\n⏸️  请在VNC中完成登录，然后按Enter键保存Cookies...")
        
        # 获取当前URL和cookies
        current_url = driver.current_url
        print(f"\n当前页面: {current_url}")
        
        # 获取所有cookies
        cookies = driver.get_cookies()
        print(f"获取到 {len(cookies)} 个cookies")
        
        # 检查是否在JavDB相关页面
        if 'javdb' in current_url.lower():
            # 检查是否有登录会话
            has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)
            
            if has_session:
                print("✅ 检测到JavDB登录会话！")
                
                # 保存cookies
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
                
                print(f"✅ Cookies已保存到: {cookie_file}")
                print("\n🎉 登录成功！现在可以使用刮削功能了。")
            else:
                print("⚠️  未检测到登录会话")
                print("提示：请确认已登录JavDB")
                
                # 仍然保存cookies（可能有用）
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
                
                print(f"ℹ️  Cookies已保存（供调试用）")
        else:
            print("⚠️  当前不在JavDB页面")
            print(f"   当前URL: {current_url}")
            print("\n建议：")
            print("1. 尝试使用VPN访问JavDB")
            print("2. 搜索JavDB镜像站点")
            print("3. 检查网络设置")
        
        # 询问是否保持浏览器开启
        keep_open = input("\n是否保持浏览器开启继续尝试？(y/n): ").lower() == 'y'
        
        if keep_open:
            print("\n浏览器保持开启中...")
            print("提示：可以继续尝试不同的方法访问JavDB")
            print("按Ctrl+C关闭浏览器")
            
            try:
                while True:
                    time.sleep(30)
                    # 定期检查并保存cookies
                    current_url = driver.current_url
                    if 'javdb' in current_url.lower():
                        cookies = driver.get_cookies()
                        has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)
                        
                        if has_session:
                            cookie_file = config_dir / "javdb_cookies.json"
                            cookie_data = {
                                "cookies": cookies,
                                "timestamp": datetime.now().isoformat(),
                                "domain": current_url
                            }
                            
                            with open(cookie_file, 'w') as f:
                                json.dump(cookie_data, f, indent=2)
                            
                            print(f"\n✅ 检测到登录，Cookies已自动保存!")
                            break
                    
            except KeyboardInterrupt:
                print("\n\n正在关闭浏览器...")
        
        driver.quit()
        print("✅ 浏览器已关闭")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("\n请确保Docker容器正在运行:")
        print("  docker compose ps")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(help_login_javdb())