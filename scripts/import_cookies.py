#!/usr/bin/env python3
"""
手动导入JavDB Cookies
如果您能在其他浏览器访问JavDB，可以导出cookies并使用此脚本导入
"""

import json
from pathlib import Path
from datetime import datetime

def import_cookies():
    """手动导入cookies"""
    
    print("=" * 60)
    print("📥 JavDB Cookies导入工具")
    print("=" * 60)
    
    print("\n步骤1: 在能访问JavDB的浏览器中获取cookies")
    print("1. 打开JavDB并登录")
    print("2. 按F12打开开发者工具")
    print("3. 进入Application/存储 -> Cookies")
    print("4. 找到_jdb_session的值")
    
    session_value = input("\n请输入_jdb_session的值: ").strip()
    
    if not session_value:
        print("❌ 未输入session值")
        return
    
    # 创建cookie格式
    cookies = [
        {
            "name": "_jdb_session",
            "value": session_value,
            "domain": ".javdb.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }
    ]
    
    # 保存到配置目录
    config_dir = Path("/Users/yaolidong/Documents/GitHub/AutoJAV/config")
    config_dir.mkdir(exist_ok=True)
    
    cookie_file = config_dir / "javdb_cookies.json"
    cookie_data = {
        "cookies": cookies,
        "timestamp": datetime.now().isoformat(),
        "domain": "https://javdb.com",
        "manual_import": True
    }
    
    with open(cookie_file, 'w') as f:
        json.dump(cookie_data, f, indent=2)
    
    print(f"\n✅ Cookies已保存到: {cookie_file}")
    print("现在可以尝试使用刮削功能了")

if __name__ == "__main__":
    import_cookies()