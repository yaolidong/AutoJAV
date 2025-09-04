# NAS 部署指南

## 概述

本指南专门为在 NAS（网络附加存储）设备上部署 AutoJAV 系统而编写，解决了 NAS 环境中常见的资源限制和兼容性问题。

## 常见问题及解决方案

### 1. CPU 限制不支持

**问题**：`NanoCPUs can not be set, as your kernel does not support CPU CFS scheduler`

**解决方案**：使用专门的 NAS 配置文件，已移除 CPU 限制。

### 2. 容器频繁崩溃

**原因**：
- 内存不足
- 健康检查太复杂
- 资源限制过高

**解决方案**：
- 降低内存限制
- 使用简化的健康检查
- 延长启动和检查时间

## 快速部署

### 步骤 1：拉取最新代码

```bash
cd /path/to/AutoJAV
git pull origin main
```

### 步骤 2：使用 NAS 专用配置

```bash
# 使用 NAS 优化的 docker-compose 文件
docker-compose -f docker-compose.nas.yml down
docker-compose -f docker-compose.nas.yml build
docker-compose -f docker-compose.nas.yml up -d
```

### 步骤 3：检查容器状态

```bash
# 查看容器状态
docker-compose -f docker-compose.nas.yml ps

# 查看日志
docker-compose -f docker-compose.nas.yml logs -f av-scraper
```

## NAS 优化配置说明

### 1. 资源限制

- **内存限制**：从 2G 降低到 800M（主服务）和 500M（Web 界面）
- **内存预留**：从 512M 降低到 256M（主服务）和 128M（Web 界面）
- **CPU 限制**：完全移除，避免内核兼容性问题

### 2. 健康检查

- **检查间隔**：从 30s 增加到 60s
- **超时时间**：从 15s 增加到 30s
- **重试次数**：从 3 次增加到 5 次
- **启动时间**：从 90s 增加到 120s
- **检查方式**：使用简单的 curl 检查代替复杂的 Python 脚本

### 3. 重启策略

- 将 `unless-stopped` 改为 `always`，确保容器崩溃后自动重启

### 4. 日志管理

- 限制日志文件大小为 5M
- 最多保留 2 个日志文件
- 避免日志占用过多存储空间

### 5. 网络模式

- Selenium Grid 使用 `host` 网络模式，避免网络通信问题
- 主服务也使用 `host` 网络模式，提高稳定性

## 环境变量配置

创建 `.env` 文件（可选）：

```bash
# 内存限制（根据 NAS 实际内存调整）
MEMORY_LIMIT=800M

# 时区设置
TZ=Asia/Shanghai

# API 配置
API_HOST=0.0.0.0
API_PORT=5555

# Web 界面配置
WEB_HOST=0.0.0.0
WEB_PORT=8899
```

## 故障排查

### 1. 容器无法启动

```bash
# 查看详细错误
docker-compose -f docker-compose.nas.yml logs --tail=50 av-scraper

# 检查资源使用
docker stats

# 手动运行健康检查
docker exec av-metadata-scraper python /app/docker/healthcheck_simple.py
```

### 2. 内存不足

如果 NAS 内存较小，可以进一步降低内存限制：

```yaml
# 编辑 docker-compose.nas.yml
deploy:
  resources:
    limits:
      memory: 500M  # 降低到 500M
    reservations:
      memory: 128M  # 降低到 128M
```

### 3. 网络连接问题

如果使用 `host` 网络模式有问题，可以改回 `bridge` 模式：

```yaml
# 移除 network_mode: host
# 添加端口映射
ports:
  - "5555:5555"
```

## 性能优化建议

1. **定期清理日志**
   ```bash
   docker exec av-metadata-scraper sh -c "echo '' > /app/logs/app.log"
   ```

2. **限制并发刮削数量**
   - 编辑 `/app/config/config.yaml`
   - 设置 `max_concurrent_scrapes: 1`

3. **禁用不必要的功能**
   - 关闭缩略图生成
   - 关闭图片下载（如果不需要）

4. **定期重启容器**
   ```bash
   # 设置 cron 任务，每天凌晨重启
   0 3 * * * docker-compose -f /path/to/docker-compose.nas.yml restart
   ```

## 监控建议

### 使用 Docker 监控

```bash
# 实时监控资源使用
watch -n 5 docker stats

# 检查容器健康状态
docker inspect av-metadata-scraper --format='{{.State.Health.Status}}'
```

### 设置告警

如果 NAS 支持，可以设置以下告警：
- 容器停止运行
- 内存使用超过 80%
- 磁盘空间不足

## 常用命令

```bash
# 启动服务
docker-compose -f docker-compose.nas.yml up -d

# 停止服务
docker-compose -f docker-compose.nas.yml down

# 重启服务
docker-compose -f docker-compose.nas.yml restart

# 查看日志
docker-compose -f docker-compose.nas.yml logs -f

# 进入容器
docker exec -it av-metadata-scraper /bin/bash

# 清理未使用的镜像和容器
docker system prune -a
```

## 支持的 NAS 型号

已测试并支持的 NAS：
- Synology DS220+, DS920+, DS1621+
- QNAP TS-253D, TS-453D
- 其他支持 Docker 的 x86_64/ARM64 NAS

## 注意事项

1. 确保 NAS 有足够的内存（建议至少 2GB）
2. 预留足够的存储空间用于视频文件
3. 定期备份配置文件和数据库
4. 监控容器运行状态，及时处理异常

## 获取帮助

如果遇到问题，请提供以下信息：
- NAS 型号和系统版本
- Docker 版本
- 错误日志（`docker-compose -f docker-compose.nas.yml logs`）
- 内存和 CPU 使用情况