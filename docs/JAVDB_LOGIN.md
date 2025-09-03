# JavDB 登录功能使用指南

## 概述

AutoJAV 支持通过半自动方式登录 JavDB 并保存 cookies，以便在刮削时获得更好的访问权限和更多的元数据信息。

通过使用持久化用户配置，您只需登录一次，后续即可在Cookie有效期内（约30天）实现自动登录。

## 功能特点

- 🔐 **半自动登录**：首次启动浏览器窗口手动登录JavDB，后续自动登录。
- 💾 **Cookie持久化**：登录成功后自动保存cookies。
- 🚀 **用户配置持久化**：将浏览器登录状态保存在一个用户配置目录中，实现长期登录。
- ✅ **自动验证**：验证保存的cookies是否有效。
- 🔄 **自动加载**：刮削时自动使用保存的cookies。
- 🗑️ **Cookie管理**：支持查看状态和清除cookies。

## 使用方法

### 方法一：通过Web UI（推荐）

1. 打开 Web UI：`http://localhost:8080`
2. 点击左侧菜单的 "JavDB登录" 选项。
3. 在登录页面中：
   - 点击 "开始登录" 按钮进行手动登录。
   - 浏览器将打开，如果这是您第一次使用或Cookie已过期，请手动完成登录（包括验证码）。
   - 如果您之前已登录，浏览器将自动处理，无需操作。
   - 登录成功后，Cookie会自动保存。

### 方法二：直接使用Python模块（命令行）

您可以通过在容器内执行Python模块来手动触发登录流程。

```bash
# 进入 av-metadata-scraper 容器
docker exec -it av-metadata-scraper bash

# 运行手动登录脚本
# 脚本会使用默认的用户配置目录 /app/config/chrome_profile
python3 -m src.utils.javdb_login --login

# 如果需要，也可以指定自定义的用户配置目录
python3 -m src.utils.javdb_login --login --user-data-dir /path/to/your/profile
```

#### 其他命令

```bash
# 验证cookies
python3 -m src.utils.javdb_login --verify

# 查看状态
python3 -m src.utils.javdb_login --status

# 清除cookies
python3 -m src.utils.javdb_login --clear
```

## 改进后的登录流程

1.  **首次启动登录**：
    *   系统会自动打开Chrome浏览器窗口，并使用位于 `config/chrome_profile` 的用户配置目录。
    *   在浏览器中输入您的JavDB账号、密码和验证码，完成登录。
    *   登录成功后，您的登录状态和Cookie会同时保存在用户配置目录和 `javdb_cookies.json` 文件中。

2.  **后续启动登录**：
    *   当您再次运行登录程序时，系统会加载之前的用户配置目录。
    *   浏览器将直接处于**已登录状态**。
    *   程序检测到已登录，自动更新 `javdb_cookies.json` 文件，全程无需任何手动操作。

## 存储位置

- **Cookies文件**：保存在容器内的 `/app/config/javdb_cookies.json`。
- **持久化用户配置**：默认保存在容器内的 `/app/config/chrome_profile` 目录。

## 注意事项

1.  **Cookie有效期**：JavDB的cookies通常有效期为30天。当Cookie过期后，您需要重新手动登录一次。
2.  **定期验证**：建议定期验证cookies是否仍然有效。
3.  **浏览器要求**：需要Chrome/Chromium浏览器支持。

## 故障排除

### 问题：浏览器无法打开

**解决方案**：
- 确保Docker容器有足够的权限。
- 检查Chrome/Chromium是否正确安装。
- 尝试重启容器。

### 问题：登录后cookies无效

**解决方案**：
- 尝试清除旧的cookies (`--clear` 命令) 后重新登录。
- 确保登录时完全加载页面。

## 安全说明

- 用户配置目录和Cookies文件包含敏感信息，请妥善保管。
- 不要将这些文件提交到版本控制系统。
- 建议定期更新cookies以保持安全性。
