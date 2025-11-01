# AutoJAV

AutoJAV 是一个面向日本 AV 内容的元数据刮削与整理系统，集成了多数据源采集、文件命名与目录归档、Web 控制台以及 Docker 化部署方案。

## 组件概览

- `av-metadata-api`：核心后端服务，负责刮削、文件整理与历史记录。
- `av-metadata-web`：Flask + Socket.IO WebUI，用于配置管理、文件浏览、日志查看与任务触发。
- `selenium-grid`：提供 Chromium WebDriver，支持需要浏览器交互的刮削流程。

## 核心特性

- 🔍 多站点刮削：支持 JavDB / JavLibrary 等数据源，并可配置优先级与镜像站。
- 🧠 智能命名：依据演员、番号、制作商等字段整理文件结构，同时生成元数据 JSON。
- 🖼️ 媒体下载：可选下载封面、海报、截图资源。
- ⚙️ 可配置化：通过 YAML/JSON 配置调节目录、代理、并发度、命名模式等参数。
- 🐳 Docker 部署：一条命令启动 Selenium、API 与 WebUI；也支持本地 Python 直接运行。

## 快速上手（Docker 推荐）

1. **克隆仓库并进入目录**
   ```bash
   git clone https://github.com/<your-account>/AutoJAV.git
   cd AutoJAV
   ```

2. **准备运行目录与配置文件**（目录不会被 Git 追踪）
   ```bash
   mkdir source organized config logs
   cp config/config.yaml.example config/config.yaml
   ```
   - 默认挂载路径可通过 `.env` 调整，示例：
     ```bash
     cat <<'EOF' > .env
     SOURCE_DIR=./source
     TARGET_DIR=./organized
     CONFIG_DIR=./config
     LOGS_DIR=./logs
     API_PORT=5555
     WEB_PORT=8080
     EOF
     ```
   - 根据实际情况修改 `config/config.yaml`（目录、代理、命名规则、刮削优先级等）。

3. **构建并启动容器栈**
   ```bash
   docker compose up --build -d
   ```

4. **访问服务**
   - WebUI：<http://localhost:8080>
   - API 健康检查：<http://localhost:5555/health>
   - Selenium Grid / VNC：<http://localhost:4444> / <http://localhost:7900>

5. **完成 WebUI 配置**
   - “配置管理”页设置源/目标目录、命名模式、成功条件。
   - “JavDB Cookie 管理”页粘贴浏览器导出的 Cookie，验证后即可在“文件管理”中执行刮削。

6. **常用运维指令**
   ```bash
   docker compose logs -f av-metadata-api       # 观察后端日志
   docker compose logs -f av-metadata-web       # 观察 WebUI 输出
   docker compose down                          # 停止并移除容器
   ```

## 本地运行（无需 Docker）

1. 安装 Python 3.9+ 与系统级依赖（Chromium/Chrome + 对应驱动）。
2. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. 准备目录与配置，同 Docker 步骤第 2 点。
4. 运行 CLI 或直接模式：
   ```bash
   python main.py --cli        # 进入命令行界面
   python main.py              # 直接按照配置执行一次任务
   python web_app.py           # 启动 WebUI（默认端口 8080）
   ```

## 配置说明

- `config/config.yaml`：主配置文件，控制目录、网络代理、刮削优先级、命名模式等。
- `config/config_with_proxy.yaml`：启用代理的参考模板。
- `config/patterns.json`：可编辑番号匹配正则及优先级。
- `config/app_config.yaml`：WebUI 默认读取的配置，可根据需要同步修改。
- `.env`：Docker Compose 环境变量（端口、挂载目录、并发参数）。

关键字段：

- `directories.source` / `directories.target`：源视频目录与整理后输出目录。
- `network.proxy_url`：HTTP / SOCKS5 代理地址（未使用时置空）。
- `scraping.priority`：刮削站点顺序，如 `"javdb","javlibrary"`。
- `organization.naming_pattern`：命名模板，支持 `{actress}`, `{code}`, `{studio}`, `{year}`, `{month}`, `{ext}`。

## 目录结构

```
AutoJAV/
├── config/                # 模板与默认配置
├── docker/                # 构建与启动脚本
├── src/
│   ├── api_server.py      # 主 API 入口
│   ├── cli/               # CLI 子命令
│   ├── models/            # 数据模型
│   ├── organizers/        # 文件整理逻辑
│   ├── scanner/           # 源目录扫描
│   ├── scrapers/          # 数据源刮削实现
│   └── utils/             # 公共工具与辅助模块
├── web/
│   ├── static/            # 前端脚本与资源
│   └── templates/         # Flask 模板
├── tests/                 # PyTest 用例
├── docker-compose.yml
├── main.py                # CLI/直接模式入口
├── web_app.py             # WebUI 入口
└── requirements.txt
```

## 开发与测试

- 运行测试：
  ```bash
  pytest
  ```
- 代码检查（可选）：
  ```bash
  black src tests
  isort src tests
  flake8 src tests
  ```
- 推荐使用 `pre-commit` 或 CI 执行上述检查，确保提交质量。

## 发布到 GitHub 的建议流程

1. 确认本地仓库干净：`git status`。
2. 运行必要的测试或集成检查，确保构建可用。
3. 根据需要在 README 中补充变更日志或版本号。
4. 提交变更：
   ```bash
   git add .
   git commit -m "chore: cleanup repository and refresh docs"
   git push origin <branch>
   ```
5. 在 GitHub 上创建 Release 或 Pull Request，并附加运行指南/截图。

## 许可证

仅供学习与研究使用。请遵守各站点服务条款与版权法规，勿用于任何商业或违法用途。