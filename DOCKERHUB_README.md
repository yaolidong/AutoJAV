# Docker Hub 部署指南

## 推送镜像到Docker Hub

### 前置要求
1. 拥有Docker Hub账户
2. 本地安装Docker
3. 登录Docker Hub

### 推送步骤

1. **登录Docker Hub**
```bash
docker login
```

2. **使用推送脚本**
```bash
# 设置你的Docker Hub用户名并运行脚本
DOCKERHUB_USERNAME=你的用户名 ./push_to_dockerhub.sh
```

或者手动推送：

3. **手动构建和推送**
```bash
# 构建镜像
docker-compose build

# 标记镜像（替换YOUR_USERNAME为你的Docker Hub用户名）
docker tag autojav-av-scraper:latest YOUR_USERNAME/autojav-scraper:latest
docker tag autojav-av-scraper-web:latest YOUR_USERNAME/autojav-web:latest

# 推送到Docker Hub
docker push YOUR_USERNAME/autojav-scraper:latest
docker push YOUR_USERNAME/autojav-web:latest
```

## 从Docker Hub部署

### 快速部署

1. **创建必要的目录**
```bash
mkdir -p autojav/{source,organized,config,logs}
cd autojav
```

2. **下载配置文件**
```bash
# 下载示例配置
wget https://raw.githubusercontent.com/yaolidong/AutoJAV/main/config/config.yaml -O config/config.yaml
wget https://raw.githubusercontent.com/yaolidong/AutoJAV/main/config/patterns.json -O config/patterns.json
```

3. **创建docker-compose.yml**
```yaml
version: '3.8'

services:
  av-scraper:
    image: YOUR_USERNAME/autojav-scraper:latest
    container_name: av-metadata-scraper
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - ./source:/app/source
      - ./organized:/app/target
      - ./config:/app/config
      - ./logs:/app/logs
      - chrome_data:/app/.chrome-data
    environment:
      - LOG_LEVEL=INFO
      - CONFIG_FILE=/app/config/config.yaml
      - TZ=Asia/Shanghai
    networks:
      - av-scraper-network

  av-scraper-web:
    image: YOUR_USERNAME/autojav-web:latest
    container_name: av-scraper-web
    restart: unless-stopped
    ports:
      - "8080:5000"
    environment:
      - FLASK_APP=web_app.py
      - CONFIG_FILE=/app/config/config.yaml
    volumes:
      - ./config:/app/config
      - ./source:/app/source
      - ./organized:/app/target
      - ./logs:/app/logs
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
```

4. **启动服务**
```bash
# 拉取镜像并启动
docker-compose pull
docker-compose up -d

# 查看日志
docker-compose logs -f
```

5. **访问Web UI**
打开浏览器访问: http://localhost:8080

### 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| SOURCE_DIR | ./source | 源视频文件目录 |
| TARGET_DIR | ./organized | 整理后的目标目录 |
| CONFIG_DIR | ./config | 配置文件目录 |
| LOGS_DIR | ./logs | 日志目录 |
| WEB_PORT | 8080 | Web UI端口 |
| LOG_LEVEL | INFO | 日志级别 |
| TZ | UTC | 时区设置 |

### 更新镜像

```bash
# 拉取最新镜像
docker-compose pull

# 重启服务
docker-compose down
docker-compose up -d
```

### 常见问题

1. **Chrome浏览器启动失败**
   - 确保容器有足够的内存（建议至少2GB）
   - 检查是否有正确的权限

2. **无法访问Web UI**
   - 检查端口是否被占用
   - 确保防火墙允许访问

3. **文件权限问题**
   - 设置正确的PUID和PGID环境变量
   - 确保挂载的目录有正确的权限

### 镜像标签

- `latest` - 最新稳定版本
- `YYYYMMDD` - 日期版本标签
- `vX.Y.Z` - 语义化版本标签（如有）

### 安全建议

1. 定期更新镜像以获取安全补丁
2. 使用环境变量或secrets管理敏感信息
3. 限制容器的资源使用
4. 使用只读挂载（如果不需要写入）

### 支持

- GitHub Issues: https://github.com/yaolidong/AutoJAV/issues
- 文档: https://github.com/yaolidong/AutoJAV/wiki