#!/bin/bash

# AutoJAV Docker快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${2}${1}${NC}"
}

# 检查Docker
if ! command -v docker &> /dev/null; then
    print_message "❌ Docker未安装，请先安装Docker Desktop" "$RED"
    print_message "   macOS: brew install --cask docker" "$YELLOW"
    print_message "   或访问: https://www.docker.com/products/docker-desktop" "$YELLOW"
    exit 1
fi

# 检查Docker是否运行
if ! docker info &> /dev/null; then
    print_message "❌ Docker未运行，请启动Docker Desktop" "$RED"
    exit 1
fi

print_message "✅ Docker已就绪" "$GREEN"

# 创建必要的目录
print_message "📁 创建必要的目录..." "$BLUE"
mkdir -p source organized config logs web/static web/templates

# 检查配置文件
if [ ! -f ".env" ]; then
    if [ -f ".env.docker" ]; then
        cp .env.docker .env
        print_message "✅ 创建环境配置文件" "$GREEN"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        print_message "✅ 创建环境配置文件" "$GREEN"
    fi
fi

# 快速启动
print_message "" "$NC"
print_message "🚀 AutoJAV Docker快速启动" "$BLUE"
print_message "=========================" "$BLUE"
print_message "" "$NC"
print_message "选择启动模式:" "$YELLOW"
print_message "1) 🌐 完整模式 (Web界面 + 刮削器) - 推荐" "$NC"
print_message "2) 🖥️  仅Web界面" "$NC"
print_message "3) 🔍 仅刮削器" "$NC"
print_message "4) 🛑 停止所有服务" "$NC"
print_message "" "$NC"

read -p "请选择 (1-4): " choice

case $choice in
    1)
        print_message "启动完整模式..." "$GREEN"
        docker compose -f docker-compose.full.yml up -d
        print_message "" "$NC"
        print_message "✅ 服务已启动!" "$GREEN"
        print_message "🌐 Web界面: http://localhost:5000" "$BLUE"
        print_message "📝 查看日志: docker compose -f docker-compose.full.yml logs -f" "$YELLOW"
        ;;
    2)
        print_message "启动Web界面..." "$GREEN"
        docker compose -f docker-compose.web.yml up -d
        print_message "" "$NC"
        print_message "✅ Web界面已启动!" "$GREEN"
        print_message "🌐 访问地址: http://localhost:5000" "$BLUE"
        ;;
    3)
        print_message "启动刮削器..." "$GREEN"
        docker compose up -d
        print_message "" "$NC"
        print_message "✅ 刮削器已启动!" "$GREEN"
        print_message "📝 查看日志: docker compose logs -f" "$YELLOW"
        ;;
    4)
        print_message "停止所有服务..." "$YELLOW"
        docker compose -f docker-compose.full.yml down
        docker compose -f docker-compose.web.yml down
        docker compose down
        print_message "✅ 所有服务已停止" "$GREEN"
        ;;
    *)
        print_message "无效选择" "$RED"
        exit 1
        ;;
esac

print_message "" "$NC"
print_message "💡 提示:" "$YELLOW"
print_message "   - 将视频文件放入 ./source 目录" "$NC"
print_message "   - 整理后的文件在 ./organized 目录" "$NC"
print_message "   - 配置文件: .env 和 config/config.yaml" "$NC"