# 🐳 AutoJAV Docker部署指南

## 快速开始 (1分钟部署)

### macOS/Linux用户

```bash
# 1. 确保Docker已安装并运行
docker --version

# 2. 快速启动
./start_docker.sh

# 3. 选择 1 (完整模式)

# 4. 访问Web界面
open http://localhost:5000
```

### Windows用户

```powershell
# 1. 确保Docker Desktop已安装并运行
docker --version

# 2. 使用部署脚本
bash deploy.sh

# 3. 选择 1 (完整部署)

# 4. 访问Web界面
start http://localhost:5000
```

## 📦 部署选项

### 选项1: 快速启动脚本 (最简单)

```bash
./start_docker.sh
```

提供4个选项：
- **1) 完整模式** - Web界面 + 刮削器 (推荐)
- **2) 仅Web界面** - 只启动Web管理界面
- **3) 仅刮削器** - 只启动后台刮削服务
- **4) 停止服务** - 停止所有运行的服务

### 选项2: 部署脚本 (更多控制)

```bash
./deploy.sh
```

提供更详细的配置选项和环境检查。

### 选项3: 手动Docker Compose

```bash
# 完整部署
docker compose -f docker-compose.full.yml up -d

# 仅Web界面
docker compose -f docker-compose.web.yml up -d

# 仅刮削器
docker compose up -d
```

## 🌐 Web界面功能

访问 http://localhost:5000 后，您可以：

1. **仪表板** - 查看系统状态和统计信息
2. **配置管理** - 实时修改刮削和整理设置
3. **文件扫描** - 查看待处理的视频文件
4. **任务管理** - 启动/停止刮削任务
5. **实时日志** - 查看处理过程的实时日志
6. **统计信息** - 查看整理结果和成功率

## 📁 目录结构

```
AutoJAV/
├── source/          # 放置原始视频文件
├── organized/       # 整理后的输出目录
│   ├── 女优名/
│   │   └── 番号/
│   │       ├── 视频文件
│   │       └── 元数据
├── config/          # 配置文件
├── logs/            # 日志文件
└── .env            # 环境变量
```

## ⚙️ 配置说明

### 基本配置 (.env文件)

```bash
# 必填：目录设置
SOURCE_DIR=./source        # 视频源文件目录
TARGET_DIR=./organized     # 整理后的目录

# 可选：JavDB登录（提高成功率）
JAVDB_USERNAME=your_username
JAVDB_PASSWORD=your_password

# 可选：性能设置
MAX_CONCURRENT_FILES=2     # 并发处理文件数
```

### 高级配置 (config/config.yaml)

```yaml
scraping:
  priority: ["javdb", "javlibrary"]  # 刮削器优先级
  
organization:
  naming_pattern: "{actress}/{code}/{code}.{ext}"  # 文件命名模式
  safe_mode: true  # 安全模式（复制而非移动）
```

## 🔧 常用命令

### 查看状态

```bash
# 查看容器状态
docker compose -f docker-compose.full.yml ps

# 查看实时日志
docker compose -f docker-compose.full.yml logs -f

# 查看资源使用
docker stats
```

### 管理服务

```bash
# 停止服务
docker compose -f docker-compose.full.yml down

# 重启服务
docker compose -f docker-compose.full.yml restart

# 更新并重启
docker compose -f docker-compose.full.yml pull
docker compose -f docker-compose.full.yml up -d
```

### 故障排查

```bash
# 进入容器调试
docker exec -it autojav-scraper bash

# 查看错误日志
docker compose -f docker-compose.full.yml logs | grep ERROR

# 清理并重建
docker compose -f docker-compose.full.yml down
docker compose -f docker-compose.full.yml build --no-cache
docker compose -f docker-compose.full.yml up -d
```

## ❓ 常见问题

### Q: 端口5000被占用怎么办？

编辑`.env`文件，修改端口：
```bash
WEB_PORT=8080
```

### Q: JavDB无法访问？

1. 检查网络连接
2. 考虑使用代理（在.env中设置）
3. 确认JavDB账号密码正确

### Q: 内存不足？

调整`.env`中的设置：
```bash
MEMORY_LIMIT=4G
MAX_CONCURRENT_FILES=1
```

### Q: 如何更新到最新版本？

```bash
git pull
docker compose -f docker-compose.full.yml build --no-cache
docker compose -f docker-compose.full.yml up -d
```

## 🚀 性能优化建议

1. **增加并发数**（如果系统资源充足）：
   ```bash
   MAX_CONCURRENT_FILES=4
   MAX_CONCURRENT_REQUESTS=6
   ```

2. **使用SSD存储**：将organized目录放在SSD上可以提高性能

3. **定期清理日志**：
   ```bash
   find logs/ -name "*.log" -mtime +7 -delete
   ```

## 🔒 安全建议

1. **修改默认密钥**：编辑`.env`中的`SECRET_KEY`
2. **设置访问限制**：如果暴露在公网，使用防火墙限制访问
3. **定期更新**：保持Docker镜像和应用程序最新

## 📝 许可和免责声明

本项目仅供学习和研究使用。请遵守相关法律法规，尊重版权和隐私。

---

需要帮助？查看 [完整文档](./DOCKER_DEPLOY.md) 或提交Issue。