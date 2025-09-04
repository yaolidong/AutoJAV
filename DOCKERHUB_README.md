# AutoJAV - Docker Hub 镜像

[![Docker Pulls](https://img.shields.io/docker/pulls/yaolidong/autojav-scraper)](https://hub.docker.com/r/yaolidong/autojav-scraper)
[![Docker Image Size](https://img.shields.io/docker/image-size/yaolidong/autojav-scraper)](https://hub.docker.com/r/yaolidong/autojav-scraper)

AutoJAV 的官方 Docker 镜像，提供自动化的视频元数据刮削和文件整理功能。

## 🚀 快速开始

### 使用 Docker Compose（推荐）

1. 创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  selenium-grid:
    image: seleniarm/standalone-chromium:latest
    container_name: selenium-grid
    restart: unless-stopped
    ports:
      - "4445:4444"
    shm_size: '2g'

  av-scraper:
    image: yaolidong/autojav-scraper:latest
    container_name: av-scraper
    restart: unless-stopped
    ports:
      - "5555:5555"
    volumes:
      - ./source:/app/source:ro
      - ./target:/app/target
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - TZ=Asia/Shanghai
      - SELENIUM_HUB_URL=http://selenium-grid:4444/wd/hub
    depends_on:
      - selenium-grid

  av-scraper-web:
    image: yaolidong/autojav-web:latest
    container_name: av-scraper-web
    restart: unless-stopped
    ports:
      - "8899:8899"
    volumes:
      - ./source:/app/source:ro
      - ./target:/app/target:ro
      - ./config:/app/config
      - ./logs:/app/logs:ro
    environment:
      - API_HOST=av-scraper
      - API_PORT=5555
    depends_on:
      - av-scraper
```

2. 启动服务：

```bash
docker-compose up -d
```

3. 访问 Web 界面：http://localhost:8899

### 使用独立容器

```bash
# 拉取镜像
docker pull yaolidong/autojav-scraper:latest
docker pull yaolidong/autojav-web:latest

# 启动 Selenium Grid
docker run -d \
  --name selenium-grid \
  -p 4445:4444 \
  --shm-size="2g" \
  seleniarm/standalone-chromium:latest

# 启动主服务
docker run -d \
  --name av-scraper \
  -p 5555:5555 \
  -v $(pwd)/source:/app/source:ro \
  -v $(pwd)/target:/app/target \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -e SELENIUM_HUB_URL=http://selenium-grid:4444/wd/hub \
  --link selenium-grid \
  yaolidong/autojav-scraper:latest

# 启动 Web 界面
docker run -d \
  --name av-scraper-web \
  -p 8899:8899 \
  -v $(pwd)/source:/app/source:ro \
  -v $(pwd)/target:/app/target:ro \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs:ro \
  -e API_HOST=av-scraper \
  -e API_PORT=5555 \
  --link av-scraper \
  yaolidong/autojav-web:latest
```

## 📦 可用镜像

### 主服务镜像
- `yaolidong/autojav-scraper:latest` - 最新稳定版
- `yaolidong/autojav-scraper:YYYYMMDD-HHMMSS` - 特定版本

### Web 界面镜像
- `yaolidong/autojav-web:latest` - 最新稳定版
- `yaolidong/autojav-web:YYYYMMDD-HHMMSS` - 特定版本

## 🔧 配置

### 目录结构

创建以下目录结构：

```
autojav/
├── source/      # 放置待处理的视频文件
├── target/      # 整理后的文件输出目录
├── config/      # 配置文件目录
│   └── config.yaml
└── logs/        # 日志文件目录
```

### 配置文件示例

创建 `config/config.yaml`：

```yaml
# 目录配置
directories:
  source: /app/source
  target: /app/target
  
# 刮削器配置
scrapers:
  javdb:
    enabled: true
    base_url: https://javdb.com
    timeout: 30
    max_retries: 3
    
# 文件组织配置
organization:
  naming_pattern: "{actress}/{code}/{code}.{ext}"
  create_metadata_files: true
  download_covers: true
  
# 支持的文件格式
supported_extensions:
  - .mp4
  - .avi
  - .mkv
  - .wmv
  - .mov
```

## 🌍 环境变量

### 通用环境变量
- `TZ` - 时区设置（默认: Asia/Shanghai）
- `PYTHONUNBUFFERED` - Python 输出缓冲（默认: 1）

### 主服务环境变量
- `API_HOST` - API 服务监听地址（默认: 0.0.0.0）
- `API_PORT` - API 服务端口（默认: 5555）
- `SELENIUM_HUB_URL` - Selenium Grid 地址

### Web 界面环境变量
- `WEB_HOST` - Web 服务监听地址（默认: 0.0.0.0）
- `WEB_PORT` - Web 服务端口（默认: 8899）
- `API_HOST` - API 服务地址
- `API_PORT` - API 服务端口

## 🔍 健康检查

两个镜像都包含健康检查：

```bash
# 检查服务健康状态
docker inspect av-scraper --format='{{.State.Health.Status}}'
docker inspect av-scraper-web --format='{{.State.Health.Status}}'
```

## 📊 资源需求

### 最低配置
- CPU: 1 核心
- 内存: 1GB
- 存储: 10GB

### 推荐配置
- CPU: 2 核心
- 内存: 2GB
- 存储: 50GB+

## 🐛 故障排查

### 查看日志

```bash
# 查看主服务日志
docker logs -f av-scraper

# 查看 Web 界面日志
docker logs -f av-scraper-web

# 查看 Selenium Grid 日志
docker logs -f selenium-grid
```

### 常见问题

1. **端口冲突**
   - 修改 docker-compose.yml 中的端口映射
   
2. **内存不足**
   - 增加 Docker 内存限制
   - 使用 NAS 优化配置

3. **网络连接问题**
   - 确保容器在同一网络中
   - 检查防火墙设置

## 🔄 更新

```bash
# 拉取最新镜像
docker pull yaolidong/autojav-scraper:latest
docker pull yaolidong/autojav-web:latest

# 重启服务
docker-compose down
docker-compose up -d
```

## 📚 相关链接

- [GitHub 仓库](https://github.com/yaolidong/AutoJAV)
- [问题反馈](https://github.com/yaolidong/AutoJAV/issues)
- [使用文档](https://github.com/yaolidong/AutoJAV/blob/main/README.md)

## 📝 许可证

MIT License - 详见 [LICENSE](https://github.com/yaolidong/AutoJAV/blob/main/LICENSE)