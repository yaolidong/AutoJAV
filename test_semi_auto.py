#!/usr/bin/env python3
"""测试半自动登录"""

import sys
import os
sys.path.insert(0, '/app')

# 设置环境变量
os.environ['CHROME_BIN'] = '/usr/bin/chromium'
os.environ['CHROMEDRIVER_PATH'] = '/usr/bin/chromedriver'

try:
    from src.utils.javdb_semi_auto_login import JavDBSemiAutoLogin
    
    print("测试半自动登录...")
    
    # 创建登录管理器
    login_manager = JavDBSemiAutoLogin(config_dir='/app/config')
    
    # 获取验证码
    print("获取验证码...")
    result = login_manager.get_login_page_with_captcha()
    
    if result['success']:
        print("✓ 成功获取验证码")
        print(f"验证码图片长度: {len(result.get('captcha_image', ''))}")
        print(f"消息: {result.get('message')}")
    else:
        print(f"✗ 获取验证码失败: {result.get('error')}")
    
    # 清理
    login_manager.cleanup()
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()