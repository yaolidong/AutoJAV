#!/usr/bin/env python3
"""测试selenium_helper"""

import sys
import os
sys.path.insert(0, '/app')

# 强制禁止Selenium下载
os.environ['SE_SKIP_DRIVER_DOWNLOAD'] = '1'
os.environ['WDM_LOCAL'] = '1'

print("测试selenium_helper...")

try:
    from src.utils.selenium_helper import get_chrome_driver
    
    print("创建Chrome驱动...")
    driver = get_chrome_driver(headless=True)
    
    print("访问测试页面...")
    driver.get("https://www.google.com")
    
    print(f"页面标题: {driver.title}")
    
    driver.quit()
    print("✓ 测试成功！")
    
except Exception as e:
    print(f"✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()