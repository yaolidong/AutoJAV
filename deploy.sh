#!/bin/bash

# AutoJAV Docker Compose 部署脚本
# 支持完整部署（Web界面 + 刮削器）

set -e  # 遇到错误立即退出

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

# 打印标题
print_title() {
    echo ""
    echo "============================================"
    echo -e "${BLUE}$1${NC}"
    echo "============================================"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_message "❌ $1 未安装" "$RED"
        return 1
    else
        print_message "✅ $1 已安装" "$GREEN"
        return 0
    fi
}

# 主函数
main() {
    print_title "🚀 AutoJAV Docker Compose 部署"
    
    # 1. 检查依赖
    print_title "📋 检查系统依赖"
    
    if ! check_command docker; then
        print_message "请先安装 Docker: https://docs.docker.com/get-docker/" "$YELLOW"
        exit 1
    fi
    
    if ! check_command docker-compose && ! docker compose version &> /dev/null; then
        print_message "请先安装 Docker Compose" "$YELLOW"
        exit 1
    fi
    
    # 确定使用的compose命令
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    print_message "使用命令: $COMPOSE_CMD" "$GREEN"
    
    # 2. 创建必要的目录
    print_title "📁 创建必要的目录"
    
    directories=("source" "organized" "config" "logs" "web/static" "web/templates")
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_message "✅ 创建目录: $dir" "$GREEN"
        else
            print_message "✅ 目录已存在: $dir" "$GREEN"
        fi
    done
    
    # 3. 准备配置文件
    print_title "⚙️ 准备配置文件"
    
    # 创建默认配置文件
    if [ ! -f "config/config.yaml" ]; then
        cat > config/config.yaml << 'EOF'
# AutoJAV 配置文件
directories:
  source: "/app/source"
  target: "/app/target"

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
  window_size: [1920, 1080]

network:
  proxy_url: ""
  max_concurrent_requests: 2
  max_concurrent_downloads: 2

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
EOF
        print_message "✅ 创建默认配置文件" "$GREEN"
    else
        print_message "✅ 配置文件已存在" "$GREEN"
    fi
    
    # 4. 准备环境变量
    print_title "🔧 配置环境变量"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.docker" ]; then
            cp .env.docker .env
            print_message "✅ 从 .env.docker 复制环境变量" "$GREEN"
        else
            cp .env.example .env
            print_message "✅ 从 .env.example 复制环境变量" "$GREEN"
        fi
        
        # 设置用户ID
        echo "" >> .env
        echo "# 自动设置的用户ID" >> .env
        echo "PUID=$(id -u)" >> .env
        echo "PGID=$(id -g)" >> .env
        print_message "✅ 设置用户权限 (UID=$(id -u), GID=$(id -g))" "$GREEN"
    else
        print_message "✅ 环境变量文件已存在" "$GREEN"
    fi
    
    # 提示用户编辑配置
    print_message "" "$NC"
    print_message "⚠️  请检查 .env 文件中的配置，特别是:" "$YELLOW"
    print_message "   - SOURCE_DIR: 视频源文件目录" "$YELLOW"
    print_message "   - TARGET_DIR: 整理后的目标目录" "$YELLOW"
    print_message "   - JAVDB_USERNAME/PASSWORD: JavDB登录凭据（可选）" "$YELLOW"
    print_message "" "$NC"
    
    # 5. 选择部署模式
    print_title "🎯 选择部署模式"
    
    echo "1) 完整部署 (Web界面 + 刮削器)"
    echo "2) 仅Web界面"
    echo "3) 仅刮削器"
    echo "4) 生产环境部署 (包含Nginx)"
    echo ""
    read -p "请选择 (1-4): " choice
    
    case $choice in
        1)
            COMPOSE_FILE="docker-compose.full.yml"
            MODE="完整部署"
            ;;
        2)
            COMPOSE_FILE="docker-compose.web.yml"
            MODE="仅Web界面"
            ;;
        3)
            COMPOSE_FILE="docker-compose.yml"
            MODE="仅刮削器"
            ;;
        4)
            COMPOSE_FILE="docker-compose.full.yml"
            COMPOSE_PROFILES="--profile production"
            MODE="生产环境"
            ;;
        *)
            print_message "无效选择" "$RED"
            exit 1
            ;;
    esac
    
    print_message "✅ 已选择: $MODE" "$GREEN"
    
    # 6. 构建和启动
    print_title "🔨 构建和启动容器"
    
    print_message "开始构建Docker镜像..." "$BLUE"
    if $COMPOSE_CMD -f $COMPOSE_FILE build ${COMPOSE_PROFILES:-}; then
        print_message "✅ 镜像构建成功" "$GREEN"
    else
        print_message "❌ 镜像构建失败" "$RED"
        exit 1
    fi
    
    print_message "启动容器..." "$BLUE"
    if $COMPOSE_CMD -f $COMPOSE_FILE up -d ${COMPOSE_PROFILES:-}; then
        print_message "✅ 容器启动成功" "$GREEN"
    else
        print_message "❌ 容器启动失败" "$RED"
        exit 1
    fi
    
    # 7. 显示容器状态
    print_title "📊 容器状态"
    $COMPOSE_CMD -f $COMPOSE_FILE ps
    
    # 8. 完成提示
    print_title "🎉 部署完成！"
    
    if [[ "$MODE" == "完整部署" ]] || [[ "$MODE" == "仅Web界面" ]] || [[ "$MODE" == "生产环境" ]]; then
        print_message "" "$NC"
        print_message "🌐 Web界面访问地址:" "$GREEN"
        
        if [[ "$MODE" == "生产环境" ]]; then
            print_message "   http://localhost" "$BLUE"
            print_message "   https://localhost (需要配置SSL证书)" "$BLUE"
        else
            print_message "   http://localhost:5000" "$BLUE"
        fi
        
        print_message "" "$NC"
        print_message "📝 Web界面功能:" "$GREEN"
        print_message "   • 配置管理 - 实时修改所有设置" "$NC"
        print_message "   • 文件扫描 - 查看待处理视频" "$NC"
        print_message "   • 任务管理 - 启动/停止刮削任务" "$NC"
        print_message "   • 实时日志 - WebSocket推送日志" "$NC"
        print_message "   • 统计信息 - 查看整理结果" "$NC"
    fi
    
    print_message "" "$NC"
    print_message "📚 常用命令:" "$GREEN"
    print_message "   查看日志: $COMPOSE_CMD -f $COMPOSE_FILE logs -f" "$NC"
    print_message "   停止服务: $COMPOSE_CMD -f $COMPOSE_FILE down" "$NC"
    print_message "   重启服务: $COMPOSE_CMD -f $COMPOSE_FILE restart" "$NC"
    print_message "   进入容器: $COMPOSE_CMD -f $COMPOSE_FILE exec autojav-scraper bash" "$NC"
    
    print_message "" "$NC"
    print_message "📁 目录说明:" "$GREEN"
    print_message "   源文件: ./source (放入视频文件)" "$NC"
    print_message "   输出: ./organized (整理后的文件)" "$NC"
    print_message "   日志: ./logs" "$NC"
    print_message "   配置: ./config/config.yaml" "$NC"
    
    print_message "" "$NC"
    print_message "✨ 祝您使用愉快！" "$BLUE"
}

# 运行主函数
main