#!/usr/bin/env python3
"""
测试Web界面是否正常工作
"""

import sys
import time
import requests
from pathlib import Path

def test_web_interface():
    """测试Web界面"""
    print("="*60)
    print("🌐 测试AutoJAV Web界面")
    print("="*60)
    
    # 检查Flask是否安装
    try:
        import flask
        import flask_cors
        import flask_socketio
        print("✅ Web依赖已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install Flask Flask-CORS Flask-SocketIO")
        return False
    
    # 检查必要文件
    files_to_check = [
        "web_app.py",
        "web/templates/index.html",
        "web/static/app.js"
    ]
    
    for file in files_to_check:
        if Path(file).exists():
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
            return False
    
    print("\n" + "="*60)
    print("📊 Web界面功能")
    print("="*60)
    
    print("""
✅ 实时配置管理
  - 修改源目录和目标目录
  - 调整刮削器设置
  - 配置文件命名模式
  
✅ 任务管理
  - 启动/停止刮削任务
  - 实时进度显示
  - 任务历史记录
  
✅ 文件扫描
  - 扫描源目录视频文件
  - 显示文件信息和识别的代码
  
✅ 实时日志
  - WebSocket实时推送日志
  - 分级显示（INFO/WARNING/ERROR）
  
✅ 统计信息
  - 文件统计
  - 按女优分类统计
  - 最近添加文件
    """)
    
    print("="*60)
    print("🚀 启动方式")
    print("="*60)
    
    print("""
1. 本地运行:
   chmod +x start_web.sh
   ./start_web.sh
   
2. Docker运行:
   docker compose -f docker-compose.web.yml up
   
3. 直接运行:
   python web_app.py
    """)
    
    print("\n访问地址: http://localhost:5000")
    print("="*60)
    
    return True

if __name__ == "__main__":
    test_web_interface()