# JavDB 登录功能使用指南

## 概述

AutoJAV 支持手动登录 JavDB 并保存 cookies，以便在刮削时获得更好的访问权限和更多的元数据信息。

## 功能特点

- 🔐 **手动登录**：打开浏览器窗口手动登录JavDB
- 💾 **Cookie持久化**：登录成功后自动保存cookies
- ✅ **自动验证**：验证保存的cookies是否有效
- 🔄 **自动加载**：刮削时自动使用保存的cookies
- 🗑️ **Cookie管理**：支持查看状态和清除cookies

## 使用方法

### 方法一：通过Web UI（推荐）

1. 打开 Web UI：http://localhost:8080
2. 点击左侧菜单的 "JavDB登录" 选项
3. 在登录页面中：
   - 查看当前Cookie状态
   - 点击 "开始登录" 按钮进行手动登录
   - 点击 "验证有效性" 检查cookies是否有效
   - 点击 "清除Cookies" 删除保存的cookies

### 方法二：通过命令行

使用提供的脚本 `javdb_login.sh`：

```bash
# 运行登录脚本
./javdb_login.sh

# 选择操作：
# 1. 手动登录JavDB
# 2. 验证保存的Cookies  
# 3. 查看Cookie状态
# 4. 清除Cookies
```

### 方法三：直接使用Python模块

```bash
# 在容器内执行
docker exec -it av-metadata-scraper bash

# 手动登录
python3 -m src.utils.javdb_login --login

# 验证cookies
python3 -m src.utils.javdb_login --verify

# 查看状态
python3 -m src.utils.javdb_login --status

# 清除cookies
python3 -m src.utils.javdb_login --clear
```

## 登录流程

1. **启动登录**：系统会自动打开Chrome浏览器窗口
2. **手动登录**：在浏览器中输入您的JavDB账号密码
3. **自动检测**：系统会自动检测登录成功
4. **保存Cookies**：登录成功后自动保存cookies到配置目录
5. **自动使用**：后续刮削时会自动加载并使用保存的cookies

## Cookie存储位置

Cookies 保存在容器内的配置目录：
- 容器内路径：`/app/config/javdb_cookies.json`
- 主机映射路径：`./config/javdb_cookies.json`

## 注意事项

1. **Cookie有效期**：JavDB的cookies通常有效期为30天
2. **定期验证**：建议定期验证cookies是否仍然有效
3. **登录失败**：如果登录失败，请检查：
   - 网络连接是否正常
   - JavDB网站是否可访问
   - 账号密码是否正确
4. **浏览器要求**：需要Chrome/Chromium浏览器支持

## 故障排除

### 问题：浏览器无法打开

**解决方案**：
- 确保Docker容器有足够的权限
- 检查Chrome/Chromium是否正确安装
- 尝试重启容器

### 问题：登录后cookies无效

**解决方案**：
- 清除旧的cookies后重新登录
- 确保登录时完全加载页面
- 检查是否有验证码或其他安全验证

### 问题：刮削时未使用cookies

**解决方案**：
- 验证cookies是否有效
- 检查刮削器配置中是否启用了登录功能
- 查看日志确认cookies是否被正确加载

## 安全说明

- Cookies文件包含敏感信息，请妥善保管
- 不要将cookies文件提交到版本控制系统
- 建议定期更新cookies以保持安全性
- 仅在受信任的环境中使用此功能

## 技术细节

### Cookie格式

保存的cookie文件格式：
```json
{
  "cookies": [...],
  "timestamp": "2024-01-01T00:00:00",
  "domain": "https://javdb.com"
}
```

### 集成方式

JavDB scraper会按以下优先级使用认证：
1. 首先尝试加载保存的cookies
2. 如果cookies无效，尝试使用LoginManager
3. 如果都失败，以未登录状态继续

### API端点

Web UI提供以下API端点：
- `POST /api/javdb/login` - 执行手动登录
- `GET /api/javdb/cookie-status` - 获取cookie状态
- `POST /api/javdb/verify-cookies` - 验证cookies有效性
- `POST /api/javdb/clear-cookies` - 清除保存的cookies