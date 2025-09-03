#!/bin/bash

# Docker Hub推送脚本
# 使用前请先登录: docker login

# 配置
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-your-dockerhub-username}"
PROJECT_NAME="autojav"
VERSION="${VERSION:-latest}"
DATE_TAG=$(date +%Y%m%d)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Docker Hub 镜像推送脚本${NC}"
echo "================================"

# 检查是否设置了Docker Hub用户名
if [ "$DOCKERHUB_USERNAME" = "your-dockerhub-username" ]; then
    echo -e "${RED}错误: 请设置DOCKERHUB_USERNAME环境变量${NC}"
    echo "使用方法: DOCKERHUB_USERNAME=你的用户名 ./push_to_dockerhub.sh"
    exit 1
fi

# 检查是否已登录Docker Hub
if ! docker info 2>/dev/null | grep -q "Username: $DOCKERHUB_USERNAME"; then
    echo -e "${YELLOW}请先登录Docker Hub:${NC}"
    docker login
    if [ $? -ne 0 ]; then
        echo -e "${RED}Docker Hub登录失败${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}使用Docker Hub用户名: $DOCKERHUB_USERNAME${NC}"
echo ""

# 构建镜像
echo -e "${YELLOW}步骤1: 构建Docker镜像...${NC}"
docker-compose build
if [ $? -ne 0 ]; then
    echo -e "${RED}镜像构建失败${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 镜像构建成功${NC}"
echo ""

# 标记镜像
echo -e "${YELLOW}步骤2: 标记镜像...${NC}"

# av-scraper服务镜像
echo "标记 av-scraper 镜像..."
docker tag autojav-av-scraper:latest $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:latest
docker tag autojav-av-scraper:latest $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:$VERSION
docker tag autojav-av-scraper:latest $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:$DATE_TAG

# av-scraper-web服务镜像
echo "标记 av-scraper-web 镜像..."
docker tag autojav-av-scraper-web:latest $DOCKERHUB_USERNAME/$PROJECT_NAME-web:latest
docker tag autojav-av-scraper-web:latest $DOCKERHUB_USERNAME/$PROJECT_NAME-web:$VERSION
docker tag autojav-av-scraper-web:latest $DOCKERHUB_USERNAME/$PROJECT_NAME-web:$DATE_TAG

echo -e "${GREEN}✓ 镜像标记完成${NC}"
echo ""

# 推送镜像
echo -e "${YELLOW}步骤3: 推送镜像到Docker Hub...${NC}"

# 推送av-scraper镜像
echo "推送 $PROJECT_NAME-scraper 镜像..."
docker push $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:latest
docker push $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:$VERSION
docker push $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:$DATE_TAG

# 推送av-scraper-web镜像
echo "推送 $PROJECT_NAME-web 镜像..."
docker push $DOCKERHUB_USERNAME/$PROJECT_NAME-web:latest
docker push $DOCKERHUB_USERNAME/$PROJECT_NAME-web:$VERSION
docker push $DOCKERHUB_USERNAME/$PROJECT_NAME-web:$DATE_TAG

echo -e "${GREEN}✓ 所有镜像推送成功!${NC}"
echo ""

# 显示推送的镜像信息
echo -e "${YELLOW}推送的镜像:${NC}"
echo "1. $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:latest"
echo "2. $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:$VERSION"
echo "3. $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:$DATE_TAG"
echo "4. $DOCKERHUB_USERNAME/$PROJECT_NAME-web:latest"
echo "5. $DOCKERHUB_USERNAME/$PROJECT_NAME-web:$VERSION"
echo "6. $DOCKERHUB_USERNAME/$PROJECT_NAME-web:$DATE_TAG"
echo ""

# 生成docker-compose.yml示例
echo -e "${YELLOW}生成用于拉取镜像的docker-compose.yml...${NC}"
cat > docker-compose.dockerhub.yml << EOF
version: '3.8'

services:
  av-scraper:
    image: $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:latest
    container_name: av-metadata-scraper
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - \${SOURCE_DIR:-./source}:/app/source
      - \${TARGET_DIR:-./organized}:/app/target
      - \${CONFIG_DIR:-./config}:/app/config
      - \${LOGS_DIR:-./logs}:/app/logs
      - chrome_data:/app/.chrome-data
    environment:
      - LOG_LEVEL=\${LOG_LEVEL:-INFO}
      - CONFIG_FILE=/app/config/config.yaml
      - PYTHONPATH=/app/src
      - PYTHONUNBUFFERED=1
      - TZ=\${TZ:-UTC}
    networks:
      - av-scraper-network
    healthcheck:
      test: ["CMD", "python", "/app/docker/healthcheck.py"]
      interval: 30s
      timeout: 15s
      retries: 3
      start_period: 90s

  av-scraper-web:
    image: $DOCKERHUB_USERNAME/$PROJECT_NAME-web:latest
    container_name: av-scraper-web
    restart: unless-stopped
    ports:
      - "\${WEB_PORT:-8080}:5000"
    environment:
      - FLASK_APP=web_app.py
      - PYTHONUNBUFFERED=1
      - CONFIG_FILE=/app/config/config.yaml
    volumes:
      - \${CONFIG_DIR:-./config}:/app/config
      - \${SOURCE_DIR:-./source}:/app/source
      - \${TARGET_DIR:-./organized}:/app/target
      - \${LOGS_DIR:-./logs}:/app/logs
    networks:
      - av-scraper-network
    depends_on:
      - av-scraper

volumes:
  chrome_data:
    driver: local

networks:
  av-scraper-network:
    driver: bridge
EOF

echo -e "${GREEN}✓ docker-compose.dockerhub.yml 已生成${NC}"
echo ""

echo -e "${GREEN}完成! 用户可以使用以下命令拉取镜像:${NC}"
echo "docker pull $DOCKERHUB_USERNAME/$PROJECT_NAME-scraper:latest"
echo "docker pull $DOCKERHUB_USERNAME/$PROJECT_NAME-web:latest"
echo ""
echo "或使用docker-compose:"
echo "docker-compose -f docker-compose.dockerhub.yml up -d"