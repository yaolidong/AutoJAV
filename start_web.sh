#!/bin/bash
# AutoJAV Web界面启动脚本

echo "=================================="
echo "🚀 AutoJAV Web界面启动器"
echo "=================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

# 检查并创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p config logs source organized web/static web/templates

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    echo "📝 创建默认配置文件..."
    cat > config/config.yaml << 'EOF'
directories:
  source: "./source"
  target: "./organized"

scraping:
  priority: ["javdb", "javlibrary"]
  max_concurrent_files: 2
  retry_attempts: 3
  timeout: 30

organization:
  naming_pattern: "{actress}/{code}/{code}.{ext}"
  conflict_resolution: "rename"
  download_images: true
  save_metadata: true
  safe_mode: true

browser:
  headless: true
  timeout: 30

network:
  proxy_url: ""
  max_concurrent_requests: 2

logging:
  level: "INFO"
EOF
    echo "✅ 配置文件已创建"
fi

# 安装依赖
echo "📦 检查并安装依赖..."
pip3 install -q Flask Flask-CORS Flask-SocketIO python-socketio 2>/dev/null

# 检查端口
PORT=${PORT:-5000}
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️ 端口 $PORT 已被占用，尝试使用其他端口..."
    PORT=$((PORT + 1))
fi

echo ""
echo "✅ 准备就绪！"
echo "=================================="
echo "🌐 Web界面地址: http://localhost:$PORT"
echo "=================================="
echo ""
echo "📌 功能说明："
echo "  • 配置管理 - 实时修改刮削和整理设置"
echo "  • 文件扫描 - 查看待处理的视频文件"
echo "  • 任务管理 - 启动/停止刮削任务"
echo "  • 实时日志 - 查看处理过程日志"
echo "  • 统计信息 - 查看整理结果统计"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=================================="
echo ""

# 启动Web应用
export FLASK_APP=web_app.py
export FLASK_ENV=development
python3 web_app.py