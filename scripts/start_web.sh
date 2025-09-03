#!/bin/bash

# 启动Selenium官方镜像的入口点脚本（它会启动VNC和浏览器）
# 我们把它放到后台运行
/opt/bin/entry_point.sh &

# 等待几秒钟，确保VNC和浏览器服务有时间初始化
sleep 5

# 启动我们的Flask Web应用
# 它会监听端口并提供Web界面
python3 /app/web_app.py
