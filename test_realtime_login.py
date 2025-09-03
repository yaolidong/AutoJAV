#!/usr/bin/env python3
"""测试实时登录功能"""

import requests
import json
import time
import base64

API_URL = "http://localhost:8899/api/javdb/login"

def test_realtime_login():
    """测试实时登录流程"""
    
    print("=== 测试 JavDB 实时登录功能 ===\n")
    
    # 1. 启动浏览器
    print("1. 启动浏览器...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "start"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 浏览器启动成功")
        print(f"   消息: {result.get('message')}")
    else:
        print(f"   ✗ 启动失败: {result.get('error')}")
        return
    
    time.sleep(2)
    
    # 2. 获取截图
    print("\n2. 获取页面截图...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "screenshot"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 截图获取成功")
        screenshot_data = result.get('screenshot', '')
        print(f"   截图数据长度: {len(screenshot_data)} bytes")
        print(f"   当前URL: {result.get('current_url')}")
        print(f"   是否已登录: {result.get('is_logged_in', False)}")
        
        # 如果是HTML内容，解码查看
        if result.get('is_html'):
            try:
                html_content = base64.b64decode(screenshot_data).decode('utf-8')
                if 'JavDB' in html_content or '登录' in html_content:
                    print("   ✓ 页面内容包含登录表单")
            except:
                pass
    else:
        print(f"   ✗ 获取失败: {result.get('error')}")
        return
    
    # 3. 模拟输入用户名
    print("\n3. 输入用户名...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "input",
        "selector": "#username",
        "text": "test_user"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 用户名输入成功")
    else:
        print(f"   ✗ 输入失败: {result.get('error')}")
    
    # 4. 模拟输入密码
    print("\n4. 输入密码...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "input",
        "selector": "#password",
        "text": "test_password"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 密码输入成功")
    else:
        print(f"   ✗ 输入失败: {result.get('error')}")
    
    # 5. 点击登录按钮
    print("\n5. 点击登录按钮...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "click",
        "selector": "button[type='submit']"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 点击成功")
        if result.get('login_success'):
            print("   ✓ 登录成功！")
    else:
        print(f"   ✗ 点击失败: {result.get('error')}")
    
    time.sleep(2)
    
    # 6. 再次获取截图确认状态
    print("\n6. 获取登录后截图...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "screenshot"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 截图获取成功")
        print(f"   是否已登录: {result.get('is_logged_in', False)}")
        print(f"   当前URL: {result.get('current_url')}")
    
    # 7. 关闭浏览器
    print("\n7. 关闭浏览器...")
    response = requests.post(API_URL, json={
        "method": "realtime",
        "action": "close"
    })
    result = response.json()
    
    if result.get('success'):
        print("   ✓ 浏览器已关闭")
    
    print("\n=== 测试完成 ===")
    print("\n说明:")
    print("- 这是一个模拟测试，展示了实时登录的工作流程")
    print("- 在实际使用中，用户可以通过Web界面看到实时的页面截图")
    print("- 用户在界面中输入真实的用户名和密码即可完成登录")
    print("- 登录成功后，Cookies会自动保存供后续使用")

if __name__ == "__main__":
    test_realtime_login()