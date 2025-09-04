# Selenium Grid 手动浏览器控制指南

## 概述
由于Selenium Grid运行在Docker容器中，无法在macOS的Applications中显示Chrome浏览器。本指南提供了多种方式来手动打开和控制Grid中的浏览器。

## 方法1: 使用VNC查看器（推荐）

### 步骤：
1. 确保Docker容器正在运行：
   ```bash
   docker compose up
   ```

2. 打开浏览器访问VNC界面：
   ```
   http://localhost:7900
   ```

3. 输入密码：`secret`

4. 点击 "Connect" 按钮，即可看到Chrome浏览器界面

### VNC界面功能：
- 实时查看浏览器操作
- 可以直接在VNC中操作浏览器（点击、输入等）
- 支持全屏模式
- 可以看到所有的网页内容和开发者工具

## 方法2: 使用Python脚本控制

### 运行脚本：
```bash
# 打开默认页面（Google）
python scripts/open_grid_browser.py

# 打开指定URL
python scripts/open_grid_browser.py https://javdb.com

# 运行网络测试
python scripts/open_grid_browser.py test
```

### 脚本功能：
- 在Selenium Grid中创建浏览器会话
- 访问指定的URL
- 保持浏览器开启状态（按Ctrl+C关闭）
- 测试网站访问性（Google、JavDB、JavLibrary）

## 方法3: 使用Web控制面板

### 使用步骤：
1. 在浏览器中打开控制面板：
   ```
   file:///Users/yaolidong/Documents/GitHub/AutoJAV/web/grid_browser_control.html
   ```

2. 界面功能：
   - **状态监控**：实时显示Selenium Grid状态
   - **快速访问VNC**：一键打开VNC界面
   - **URL导航**：输入网址并导航
   - **快速操作**：预设的常用网站快捷访问
   - **网络测试**：测试各网站的可访问性

## 方法4: 使用命令行直接控制

### 使用curl命令查看Grid状态：
```bash
# 查看Grid状态
curl http://localhost:4444/status

# 查看活动会话
curl http://localhost:4444/se/grid/newsession
```

### 使用Python交互式控制：
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 配置选项
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# 连接到Grid
driver = webdriver.Remote(
    command_executor='http://localhost:4444/wd/hub',
    options=options
)

# 访问网站
driver.get('https://www.google.com')

# 保持浏览器开启
input("按Enter键关闭浏览器...")
driver.quit()
```

## 常见问题

### Q: 为什么在Applications中看不到Chrome？
A: Selenium Grid运行在Docker容器中，是一个隔离的环境。浏览器实例存在于容器内部，不会出现在macOS的Applications文件夹中。

### Q: VNC连接失败怎么办？
A: 
1. 确保Docker容器正在运行：`docker compose ps`
2. 检查端口7900是否被占用：`lsof -i :7900`
3. 重启容器：`docker compose restart av-scraper-web`

### Q: 如何同时打开多个浏览器会话？
A: 运行多个Python脚本实例，每个实例会创建独立的浏览器会话。Selenium Grid支持最多10个并发会话。

### Q: 如何查看浏览器的开发者工具？
A: 在VNC界面中，按F12或右键选择"检查"即可打开Chrome开发者工具。

### Q: 如何使用代理访问被封锁的网站？
A: 修改Chrome选项添加代理：
```python
options.add_argument('--proxy-server=http://your-proxy:port')
```

## 端口说明

| 端口 | 用途 | 访问地址 |
|------|------|----------|
| 4444 | Selenium Grid Hub | http://localhost:4444 |
| 7900 | VNC Web界面 | http://localhost:7900 |
| 8899 | Web应用界面 | http://localhost:8899 |
| 5555 | API服务 | http://localhost:5555 |

## 调试技巧

1. **查看Grid控制台**：
   访问 http://localhost:4444/ui 查看Grid的管理界面

2. **查看容器日志**：
   ```bash
   docker compose logs av-scraper-web -f
   ```

3. **进入容器内部**：
   ```bash
   docker exec -it av-scraper-web /bin/bash
   ```

4. **截图调试**：
   在Python脚本中添加：
   ```python
   driver.save_screenshot('debug.png')
   ```

## 注意事项

- VNC密码是固定的：`secret`
- 浏览器会话有超时限制（默认300秒无操作）
- 同时运行的会话数有限制（默认最多10个）
- 网络访问受限的网站需要使用VPN或代理