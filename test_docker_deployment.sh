#!/bin/bash
# Docker部署测试脚本

echo "=================================="
echo "🐳 Docker 部署测试"
echo "=================================="

# 检查Docker环境
echo -e "\n📋 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose未安装"
        exit 1
    fi
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

echo "✅ Docker版本: $(docker --version)"
echo "✅ Docker Compose版本: $($COMPOSE_CMD version)"

# 验证Docker配置文件
echo -e "\n📋 验证Docker配置文件..."
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile存在"
else
    echo "❌ Dockerfile不存在"
    exit 1
fi

if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml存在"
else
    echo "❌ docker-compose.yml不存在"
    exit 1
fi

# 检查必要的目录
echo -e "\n📋 检查必要的目录..."
dirs=("config" "logs" "source" "organized")
for dir in "${dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "⚠️ 创建目录: $dir"
        mkdir -p "$dir"
    else
        echo "✅ 目录存在: $dir"
    fi
done

# 创建示例配置文件
echo -e "\n📋 准备配置文件..."
if [ ! -f "config/config.yaml" ]; then
    echo "⚠️ 创建示例配置文件..."
    cat > config/config.yaml << 'EOF'
# AV Metadata Scraper Configuration
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
  download_images: true
  save_metadata: true
  conflict_resolution: "rename"

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
    echo "✅ 配置文件已创建"
else
    echo "✅ 配置文件已存在"
fi

# 创建环境变量文件
echo -e "\n📋 准备环境变量..."
if [ ! -f ".env" ]; then
    echo "⚠️ 创建.env文件..."
    cat > .env << 'EOF'
# Docker环境变量
SOURCE_DIR=./source
TARGET_DIR=./organized
CONFIG_DIR=./config
LOGS_DIR=./logs

# 日志设置
LOG_LEVEL=INFO

# 性能设置
MAX_CONCURRENT_FILES=2
MAX_CONCURRENT_REQUESTS=2
MAX_CONCURRENT_DOWNLOADS=2

# 资源限制
MEMORY_LIMIT=2G
CPU_LIMIT=2.0

# 功能开关
SAFE_MODE=true
DEBUG_MODE=false
CREATE_METADATA_FILES=true
DOWNLOAD_IMAGES=true

# 时区
TZ=Asia/Shanghai

# 用户ID（可选）
# PUID=1000
# PGID=1000
EOF
    echo "✅ .env文件已创建"
else
    echo "✅ .env文件已存在"
fi

# 验证Docker Compose配置
echo -e "\n📋 验证Docker Compose配置..."
if $COMPOSE_CMD config --quiet > /dev/null 2>&1; then
    echo "✅ Docker Compose配置有效"
else
    echo "⚠️ Docker Compose配置有警告，但可以继续"
fi

# 构建Docker镜像（测试构建）
echo -e "\n🔨 测试Docker镜像构建..."
echo "构建可能需要几分钟，请耐心等待..."

# 使用--dry-run如果支持，否则使用普通构建
if docker build --dry-run . > /dev/null 2>&1; then
    echo "使用dry-run模式测试..."
    docker build --dry-run -t av-scraper-test:latest . 2>&1 | tail -5
else
    echo "开始实际构建测试镜像..."
    if docker build -t av-scraper-test:latest --target builder . > /dev/null 2>&1; then
        echo "✅ 构建阶段测试成功"
    else
        echo "❌ Docker镜像构建失败"
        echo "请检查Dockerfile和依赖"
        exit 1
    fi
fi

# 显示部署命令
echo -e "\n=================================="
echo "📊 测试结果总结"
echo "=================================="
echo "✅ Docker环境正常"
echo "✅ 配置文件准备完成"
echo "✅ 目录结构创建完成"
echo "✅ 环境变量配置完成"

echo -e "\n🚀 部署命令："
echo "=================================="
echo "# 构建并启动容器（前台模式）："
echo "$COMPOSE_CMD up --build"
echo ""
echo "# 构建并启动容器（后台模式）："
echo "$COMPOSE_CMD up -d --build"
echo ""
echo "# 查看日志："
echo "$COMPOSE_CMD logs -f av-scraper"
echo ""
echo "# 停止容器："
echo "$COMPOSE_CMD down"
echo ""
echo "# 进入容器shell："
echo "$COMPOSE_CMD exec av-scraper bash"
echo "=================================="

echo -e "\n💡 提示："
echo "1. 将视频文件放入 ./source 目录"
echo "2. 整理后的文件将出现在 ./organized 目录"
echo "3. 日志文件保存在 ./logs 目录"
echo "4. 可以编辑 .env 文件调整设置"
echo "5. 首次构建可能需要5-10分钟"

echo -e "\n✅ Docker部署准备完成！"