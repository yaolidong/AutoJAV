# JavDB 登录解决方案

## 问题总结
1. **网络限制**: JavDB在您的网络环境中被封锁 (net::ERR_CONNECTION_CLOSED)
2. **Cookie保存错误**: "未能保存Cookies: undefined" - 已修复代码，等待Docker重建
3. **浏览器显示问题**: Selenium Grid中的浏览器不会在VNC桌面显示（设计如此）

## 解决方案

### 方案1: 使用Login Helper脚本（推荐）
```bash
# 运行登录助手脚本
python scripts/javdb_login_helper.py
```
这个脚本会：
- 在Selenium Grid中打开浏览器
- 提供VNC访问地址 (http://localhost:7900)
- 指导您使用VPN或镜像站点访问JavDB
- 自动检测并保存登录Cookies

### 方案2: 使用VPN或代理
由于JavDB被网络封锁，您需要：
1. 在系统级别使用VPN
2. 或者搜索JavDB镜像站点（搜索 "javdb mirror" 或 "javdb proxy"）
3. 使用可访问的镜像站点登录

### 方案3: 手动保存Cookies
如果您能在其他浏览器中访问JavDB：
1. 使用浏览器开发者工具导出Cookies
2. 手动创建 `/config/javdb_cookies.json` 文件
3. 格式如下：
```json
{
  "cookies": [
    {
      "name": "_jdb_session",
      "value": "您的session值",
      "domain": ".javdb.com",
      "path": "/"
    }
  ],
  "timestamp": "2025-01-01T00:00:00",
  "domain": "https://javdb.com"
}
```

## Docker容器重建
容器正在重建中，完成后Cookie保存功能将正常工作：
```bash
# 检查构建状态
docker compose ps

# 构建完成后重启容器
docker compose up -d av-scraper-web
```

## VNC访问说明
- **地址**: http://localhost:7900
- **密码**: secret
- **说明**: VNC中看到的是Selenium Grid的浏览器会话，不是桌面应用

## 测试脚本列表
- `scripts/javdb_login_helper.py` - 登录助手（推荐）
- `scripts/vnc_browser_session.py` - VNC浏览器会话
- `scripts/open_javdb_browser.py` - 打开JavDB浏览器
- `scripts/manual_login.py` - 手动登录脚本

## 注意事项
1. Selenium Grid的浏览器是独立运行的，不会在VNC桌面显示图标
2. JavDB被封锁是网络问题，需要使用VPN或镜像站点
3. Cookie保存功能已修复，但需要容器重建才能生效

## 后续步骤
1. 等待Docker容器构建完成
2. 使用VPN或找到可访问的JavDB镜像站点
3. 运行登录助手脚本完成登录
4. 登录成功后即可正常使用刮削功能