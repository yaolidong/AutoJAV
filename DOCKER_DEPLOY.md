# 🐳 AutoJAV Docker Compose 部署指南

本文档详细说明如何使用Docker Compose部署AutoJAV项目（包含Web管理界面）。

## 📋 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [常见问题](#常见问题)
- [维护指南](#维护指南)

## 🔧 系统要求

### 最低要求
- **Docker**: 20.10+
- **Docker Compose**: 2.0+ 或 docker-compose 1.29+
- **内存**: 2GB RAM
- **存储**: 10GB可用空间
- **CPU**: 双核处理器

### 推荐配置
- **内存**: 4GB+ RAM
- **存储**: 50GB+ (用于存储视频和图片)
- **CPU**: 四核处理器
- **网络**: 稳定的互联网连接

## 🚀 快速开始

### 一键部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd AutoJAV

# 2. 运行部署脚本
chmod +x deploy.sh
./deploy.sh

# 3. 选择部署模式
# 选择 1 - 完整部署（推荐）
```

部署完成后，访问 http://localhost:5000 进入Web管理界面。

## 📝 详细部署步骤

### 步骤1: 准备环境

```bash
# 安装Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker (macOS)
brew install --cask docker

# 验证安装
docker --version
docker compose version
```

### 步骤2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.docker .env

# 编辑环境变量
vim .env
```

**重要配置项：**

```env
# 必须配置的目录
SOURCE_DIR=./source          # 放置原始视频文件
TARGET_DIR=./organized       # 整理后的输出目录

# Web界面端口
WEB_PORT=5000

# JavDB登录（可选，但推荐）
JAVDB_USERNAME=your_username
JAVDB_PASSWORD=your_password

# 时区设置
TZ=Asia/Shanghai
```

### 步骤3: 创建必要目录

```bash
mkdir -p source organized config logs
```

### 步骤4: 选择部署方式

#### 方式A: 使用部署脚本（推荐）

```bash
./deploy.sh
```

选择选项：
- `1` - 完整部署（Web界面 + 刮削器）✅ 推荐
- `2` - 仅Web界面
- `3` - 仅刮削器
- `4` - 生产环境（包含Nginx）

#### 方式B: 手动Docker Compose

```bash
# 完整部署
docker compose -f docker-compose.full.yml up -d

# 查看日志
docker compose -f docker-compose.full.yml logs -f

# 停止服务
docker compose -f docker-compose.full.yml down
```

## ⚙️ 配置说明

### 目录结构

```
AutoJAV/
├── source/          # 视频源文件目录
├── organized/       # 整理后的目录
│   ├── 女优名/
│   │   └── 番号/
│   │       ├── 番号.mp4
│   │       └── 番号.json
├── config/          # 配置文件
│   └── config.yaml
├── logs/            # 日志文件
└── .env            # 环境变量
```

### 配置文件 (config/config.yaml)

```yaml
# 目录配置
directories:
  source: "/app/source"
  target: "/app/target"

# 刮削配置
scraping:
  priority: ["javdb", "javlibrary"]
  max_concurrent_files: 2
  timeout: 30

# 文件整理
organization:
  naming_pattern: "{actress}/{code}/{code}.{ext}"
  conflict_resolution: "rename"
  safe_mode: true
  download_images: true
  save_metadata: true
```

### 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SOURCE_DIR` | ./source | 视频源文件目录 |
| `TARGET_DIR` | ./organized | 整理后的目录 |
| `WEB_PORT` | 5000 | Web界面端口 |
| `JAVDB_USERNAME` | - | JavDB用户名 |
| `JAVDB_PASSWORD` | - | JavDB密码 |
| `MAX_CONCURRENT_FILES` | 2 | 并发处理文件数 |
| `SAFE_MODE` | true | 安全模式(复制而非移动) |
| `LOG_LEVEL` | INFO | 日志级别 |
| `TZ` | Asia/Shanghai | 时区 |

## 🖥️ 使用指南

### 访问Web界面

1. 打开浏览器访问: http://localhost:5000
2. 界面功能：
   - **仪表板**: 查看系统状态和统计
   - **配置管理**: 实时修改所有设置
   - **文件扫描**: 查看待处理的视频文件
   - **任务管理**: 启动/停止刮削任务
   - **实时日志**: 查看处理过程
   - **统计信息**: 查看整理结果

### 使用流程

1. **准备文件**
   ```bash
   # 将视频文件放入source目录
   cp /path/to/videos/*.mp4 ./source/
   ```

2. **配置设置**
   - 访问Web界面 → 配置管理
   - 设置刮削器优先级
   - 配置文件命名模式
   - 保存配置

3. **开始处理**
   - 访问Web界面 → 文件扫描
   - 扫描源目录
   - 访问任务管理 → 开始任务

4. **查看结果**
   ```bash
   # 查看整理后的文件
   ls -la ./organized/
   ```

## 🛠️ 常用命令

### 容器管理

```bash
# 查看容器状态
docker compose -f docker-compose.full.yml ps

# 查看日志
docker compose -f docker-compose.full.yml logs -f

# 重启服务
docker compose -f docker-compose.full.yml restart

# 停止服务
docker compose -f docker-compose.full.yml down

# 停止并删除数据
docker compose -f docker-compose.full.yml down -v
```

### 进入容器

```bash
# 进入刮削器容器
docker exec -it autojav-scraper bash

# 进入Web容器
docker exec -it autojav-web bash
```

### 查看资源使用

```bash
# 实时监控
docker stats

# 查看磁盘使用
docker system df
```

## ❓ 常见问题

### Q1: 端口被占用

```bash
# 修改.env中的端口
WEB_PORT=8080

# 重新启动
docker compose -f docker-compose.full.yml up -d
```

### Q2: 权限问题

```bash
# 设置正确的用户ID
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env

# 修复目录权限
sudo chown -R $(id -u):$(id -g) source/ organized/ logs/
```

### Q3: JavDB无法访问

- 检查网络连接
- 考虑使用代理：
  ```env
  HTTP_PROXY=http://proxy:8080
  HTTPS_PROXY=http://proxy:8080
  ```

### Q4: 内存不足

```bash
# 增加内存限制
echo "MEMORY_LIMIT=4G" >> .env

# 减少并发数
echo "MAX_CONCURRENT_FILES=1" >> .env
```

### Q5: Chrome启动失败

```bash
# 重建镜像
docker compose -f docker-compose.full.yml build --no-cache

# 检查Chrome版本
docker exec autojav-scraper google-chrome --version
```

## 🔧 维护指南

### 定期维护

```bash
# 每周清理日志
find logs/ -name "*.log" -mtime +7 -delete

# 每月更新镜像
docker compose -f docker-compose.full.yml pull
docker compose -f docker-compose.full.yml up -d

# 清理未使用的镜像
docker image prune -a
```

### 备份数据

```bash
# 备份配置
tar -czf backup-config-$(date +%Y%m%d).tar.gz config/ .env

# 备份整理后的文件
tar -czf backup-organized-$(date +%Y%m%d).tar.gz organized/
```

### 性能优化

```bash
# 调整并发数
MAX_CONCURRENT_FILES=4  # 增加并发

# 调整资源限制
MEMORY_LIMIT=4G
CPU_LIMIT=4.0
```

## 🔒 安全建议

1. **修改默认密钥**
   ```env
   SECRET_KEY=your-unique-secret-key-$(openssl rand -hex 32)
   ```

2. **限制访问**
   - 使用防火墙限制端口访问
   - 配置Nginx反向代理
   - 添加基础认证

3. **定期更新**
   ```bash
   git pull
   docker compose -f docker-compose.full.yml build
   docker compose -f docker-compose.full.yml up -d
   ```

## 📊 监控

### 使用Portainer（可选）

```bash
# 安装Portainer
docker volume create portainer_data
docker run -d -p 9000:9000 \
  --name=portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce
```

访问 http://localhost:9000 管理容器。

## 🆘 获取帮助

- 查看日志: `docker compose logs -f`
- 检查配置: `docker compose config`
- 项目文档: 查看 README.md
- 提交问题: GitHub Issues

## 📝 更新日志

- v1.0.0 - 初始版本，支持Web界面和Docker Compose部署
- 支持JavDB刮削
- 自动文件整理
- 实时日志查看
- 配置管理界面

---

**提示**: 首次运行可能需要5-10分钟来构建镜像，请耐心等待。

**注意**: 请遵守相关法律法规，仅用于个人学习和研究目的。