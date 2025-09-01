#!/bin/bash

# AutoJAV部署验证脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印消息
print_message() {
    echo -e "${2}${1}${NC}"
}

print_message "🔍 AutoJAV部署验证" "$BLUE"
print_message "===================" "$BLUE"
echo ""

# 检查结果统计
PASS=0
FAIL=0

# 检查函数
check() {
    if eval "$2" &> /dev/null; then
        print_message "✅ $1" "$GREEN"
        ((PASS++))
    else
        print_message "❌ $1" "$RED"
        ((FAIL++))
    fi
}

# 1. 检查Docker
print_message "📦 检查Docker环境..." "$YELLOW"
check "Docker已安装" "command -v docker"
check "Docker正在运行" "docker info"
check "Docker Compose可用" "docker compose version"
echo ""

# 2. 检查核心文件
print_message "📄 检查核心文件..." "$YELLOW"
check "Dockerfile存在" "[ -f Dockerfile ]"
check "Dockerfile.web存在" "[ -f Dockerfile.web ]"
check "docker-compose.yml存在" "[ -f docker-compose.yml ]"
check "docker-compose.full.yml存在" "[ -f docker-compose.full.yml ]"
check "deploy.sh脚本存在" "[ -f deploy.sh ]"
check "start_docker.sh脚本存在" "[ -f start_docker.sh ]"
echo ""

# 3. 检查Web应用文件
print_message "🌐 检查Web应用文件..." "$YELLOW"
check "web_app.py存在" "[ -f web_app.py ]"
check "Web模板存在" "[ -f web/templates/index.html ]"
check "JavaScript文件存在" "[ -f web/static/app.js ]"
echo ""

# 4. 检查配置文件
print_message "⚙️ 检查配置文件..." "$YELLOW"
check ".env.docker模板存在" "[ -f .env.docker ]"
check ".env.example存在" "[ -f .env.example ]"
if [ -f .env ]; then
    check ".env配置存在" "true"
else
    print_message "⚠️  .env配置不存在（将在部署时创建）" "$YELLOW"
fi
echo ""

# 5. 检查目录结构
print_message "📁 检查目录结构..." "$YELLOW"
check "source目录" "[ -d source ] || mkdir -p source"
check "organized目录" "[ -d organized ] || mkdir -p organized"
check "config目录" "[ -d config ] || mkdir -p config"
check "logs目录" "[ -d logs ] || mkdir -p logs"
check "web/static目录" "[ -d web/static ] || mkdir -p web/static"
check "web/templates目录" "[ -d web/templates ] || mkdir -p web/templates"
echo ""

# 6. 检查Docker Compose配置
print_message "🐳 验证Docker Compose配置..." "$YELLOW"
check "docker-compose.yml语法" "docker compose -f docker-compose.yml config --quiet"
check "docker-compose.full.yml语法" "docker compose -f docker-compose.full.yml config --quiet"
echo ""

# 7. 检查Python源代码
print_message "🐍 检查Python源代码..." "$YELLOW"
check "主程序存在" "[ -f main.py ]"
check "刮削器模块存在" "[ -d src/scrapers ]"
check "整理器模块存在" "[ -d src/organizers ]"
check "JavDB刮削器存在" "[ -f src/scrapers/javdb_scraper.py ]"
check "文件整理器存在" "[ -f src/organizers/file_organizer.py ]"
echo ""

# 8. 检查文档
print_message "📚 检查文档..." "$YELLOW"
check "README.md存在" "[ -f README.md ]"
check "Docker部署文档存在" "[ -f DOCKER_DEPLOY.md ] || [ -f DOCKER_DEPLOYMENT.md ]"
check "Docker快速指南存在" "[ -f DOCKER_README.md ]"
echo ""

# 9. 总结
print_message "📊 验证结果" "$BLUE"
print_message "===================" "$BLUE"
print_message "✅ 通过: $PASS 项" "$GREEN"
if [ $FAIL -gt 0 ]; then
    print_message "❌ 失败: $FAIL 项" "$RED"
else
    print_message "🎉 所有检查通过！" "$GREEN"
fi
echo ""

# 10. 下一步建议
if [ $FAIL -eq 0 ]; then
    print_message "🚀 系统已准备就绪！您可以：" "$GREEN"
    print_message "" "$NC"
    print_message "1. 快速启动:" "$YELLOW"
    print_message "   ./start_docker.sh" "$NC"
    print_message "" "$NC"
    print_message "2. 使用部署脚本:" "$YELLOW"
    print_message "   ./deploy.sh" "$NC"
    print_message "" "$NC"
    print_message "3. 手动启动:" "$YELLOW"
    print_message "   docker compose -f docker-compose.full.yml up -d" "$NC"
    print_message "" "$NC"
    print_message "启动后访问: http://localhost:5000" "$BLUE"
else
    print_message "⚠️  请先解决上述问题后再部署" "$YELLOW"
    print_message "" "$NC"
    print_message "常见解决方案:" "$YELLOW"
    print_message "1. 安装Docker: brew install --cask docker" "$NC"
    print_message "2. 启动Docker: 打开Docker Desktop应用" "$NC"
    print_message "3. 创建目录: mkdir -p source organized config logs" "$NC"
fi