#!/usr/bin/env python3
"""测试浏览器启动"""

import sys
import os
sys.path.insert(0, '/app/src')

# 设置环境变量
os.environ['CHROME_BIN'] = '/usr/bin/chromium'
os.environ['CHROMEDRIVER_PATH'] = '/usr/bin/chromedriver'

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    print("开始测试浏览器启动...")
    
    # 创建选项
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 尝试不同的方式创建driver
    print("\n方法1: 让Selenium自动查找...")
    try:
        driver = webdriver.Chrome(options=options)
        print("✓ 成功使用自动查找")
        driver.quit()
    except Exception as e:
        print(f"✗ 自动查找失败: {e}")
    
    print("\n方法2: 指定chromedriver路径...")
    try:
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        print("✓ 成功使用指定路径")
        driver.quit()
    except Exception as e:
        print(f"✗ 指定路径失败: {e}")
    
    print("\n方法3: 使用browser_helper...")
    try:
        from utils.browser_helper import create_chrome_driver
        driver = create_chrome_driver(headless=True)
        print("✓ 成功使用browser_helper")
        driver.quit()
    except Exception as e:
        print(f"✗ browser_helper失败: {e}")
    
    print("\n检查文件存在性:")
    print(f"Chromium: {os.path.exists('/usr/bin/chromium')}")
    print(f"ChromeDriver: {os.path.exists('/usr/bin/chromedriver')}")
    
    # 检查版本
    import subprocess
    try:
        result = subprocess.run(['/usr/bin/chromium', '--version'], capture_output=True, text=True)
        print(f"Chromium版本: {result.stdout.strip()}")
    except:
        pass
    
    try:
        result = subprocess.run(['/usr/bin/chromedriver', '--version'], capture_output=True, text=True)
        print(f"ChromeDriver版本: {result.stdout.strip()}")
    except:
        pass
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()