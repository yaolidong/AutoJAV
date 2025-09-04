#!/bin/bash

# Docker Hub 推送脚本
# 使用方法: ./push_to_dockerhub.sh [dockerhub-username]

set -e

# Docker Hub 用户名
DOCKER_USER=${1:-"yaolidong"}
VERSION=$(date +%Y%m%d-%H%M%S)
LATEST_TAG="latest"

echo "🚀 开始构建并推送到 Docker Hub"
echo "Docker Hub 用户名: $DOCKER_USER"
echo "版本标签: $VERSION"

# 确保已登录 Docker Hub
echo "📝 请确保已登录 Docker Hub (docker login)"
read -p "是否已登录? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "请先运行: docker login"
    exit 1
fi

# 构建镜像
echo "🔨 构建主服务镜像..."
docker build -t autojav-scraper:$VERSION -f Dockerfile .
docker build -t autojav-scraper:$LATEST_TAG -f Dockerfile .

echo "🔨 构建Web界面镜像..."
docker build -t autojav-web:$VERSION -f Dockerfile.web .
docker build -t autojav-web:$LATEST_TAG -f Dockerfile.web .

# 标记镜像
echo "🏷️ 标记镜像..."
docker tag autojav-scraper:$VERSION $DOCKER_USER/autojav-scraper:$VERSION
docker tag autojav-scraper:$LATEST_TAG $DOCKER_USER/autojav-scraper:$LATEST_TAG
docker tag autojav-web:$VERSION $DOCKER_USER/autojav-web:$VERSION
docker tag autojav-web:$LATEST_TAG $DOCKER_USER/autojav-web:$LATEST_TAG

# 推送镜像
echo "📤 推送主服务镜像到 Docker Hub..."
docker push $DOCKER_USER/autojav-scraper:$VERSION
docker push $DOCKER_USER/autojav-scraper:$LATEST_TAG

echo "📤 推送Web界面镜像到 Docker Hub..."
docker push $DOCKER_USER/autojav-web:$VERSION
docker push $DOCKER_USER/autojav-web:$LATEST_TAG

# 创建多架构镜像 (可选)
echo "🌍 创建多架构支持..."
read -p "是否创建多架构镜像? (需要 docker buildx) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 创建 buildx builder
    docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch
    
    # 构建并推送多架构镜像
    echo "🔨 构建多架构主服务镜像..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t $DOCKER_USER/autojav-scraper:$VERSION \
        -t $DOCKER_USER/autojav-scraper:$LATEST_TAG \
        -f Dockerfile \
        --push .
    
    echo "🔨 构建多架构Web界面镜像..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t $DOCKER_USER/autojav-web:$VERSION \
        -t $DOCKER_USER/autojav-web:$LATEST_TAG \
        -f Dockerfile.web \
        --push .
fi

echo "✅ 完成！"
echo ""
echo "📦 已推送的镜像："
echo "  - $DOCKER_USER/autojav-scraper:$VERSION"
echo "  - $DOCKER_USER/autojav-scraper:$LATEST_TAG"
echo "  - $DOCKER_USER/autojav-web:$VERSION"
echo "  - $DOCKER_USER/autojav-web:$LATEST_TAG"
echo ""
echo "📖 使用方法："
echo "  docker pull $DOCKER_USER/autojav-scraper:latest"
echo "  docker pull $DOCKER_USER/autojav-web:latest"
echo ""
echo "🎯 或使用 docker-compose："
echo "  请参考 docker-compose.dockerhub.yml"