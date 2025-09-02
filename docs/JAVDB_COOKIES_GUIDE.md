# JavDB Cookies 完整使用指南

## ✅ 问题已解决

您的cookies已经成功保存并验证有效！

## 当前状态

- **Cookies状态**: ✅ 有效
- **登录状态**: ✅ 已登录
- **Cookie数量**: 11个
- **保存位置**: `/app/config/javdb_cookies.json`

## 如何获取和保存JavDB Cookies

### 方法一：使用浏览器开发者工具（推荐）

1. **在浏览器中登录JavDB**
   - 打开 https://javdb.com
   - 输入账号密码登录

2. **导出Cookies**
   - 按 F12 打开开发者工具
   - 切换到 Application（应用程序）或 Storage（存储）标签
   - 在左侧找到 Cookies → javdb.com
   - 选中所有cookies并复制

3. **保存Cookies到文件**
   创建 `javdb_cookies.json` 文件，格式如下：
   ```json
   {
     "cookies": [
       {
         "name": "cookie_name",
         "value": "cookie_value",
         "domain": ".javdb.com",
         "path": "/",
         "secure": false,
         "httpOnly": false,
         "sameSite": "Lax"
       }
     ],
     "timestamp": "2025-09-01T14:33:50.105246",
     "domain": "https://javdb.com"
   }
   ```

4. **复制到容器**
   ```bash
   docker cp javdb_cookies.json av-metadata-scraper:/app/config/
   docker cp javdb_cookies.json av-scraper-web:/app/config/
   ```

### 方法二：使用主机脚本（需要Python环境）

```bash
# 运行辅助脚本
python3 javdb_cookie_helper.py

# 复制到容器
docker cp ./config/javdb_cookies.json av-metadata-scraper:/app/config/
docker cp ./config/javdb_cookies.json av-scraper-web:/app/config/
```

## 验证Cookies

### 在容器中验证

```bash
# 修复并验证cookies
docker exec av-metadata-scraper python3 -m src.utils.javdb_cookie_import --fix --verify
```

### 通过Web UI验证

1. 访问 http://localhost:8080
2. 点击"JavDB登录"标签
3. 查看Cookie状态
4. 点击"验证有效性"按钮

## 常见问题

### Q: 为什么显示cookies已过期？

**A**: 通常是格式问题，运行修复命令：
```bash
docker exec av-metadata-scraper python3 -m src.utils.javdb_cookie_import --fix
```

### Q: 如何知道cookies是否真的有效？

**A**: 查看验证结果中的以下指标：
- `logout_link_found: true` - 找到登出链接
- `user_menu_found: true` - 找到用户菜单
- `user_page_accessible: true` - 可以访问用户页面

### Q: Cookies能用多久？

**A**: JavDB的cookies通常有效期为30天，建议定期更新。

### Q: 为什么Web UI验证失败但容器验证成功？

**A**: Web容器可能没有Chrome浏览器。直接在metadata-scraper容器中验证更准确。

## Cookie字段说明

| 字段 | 说明 | 必需 |
|------|------|------|
| name | Cookie名称 | ✅ |
| value | Cookie值 | ✅ |
| domain | 域名（建议使用`.javdb.com`） | ✅ |
| path | 路径（通常是`/`） | ✅ |
| secure | 是否仅HTTPS | ❌ |
| httpOnly | 是否仅HTTP访问 | ❌ |
| sameSite | 同站策略（使用`Lax`） | ❌ |
| expiry | 过期时间（Unix时间戳） | ❌ |

## 最佳实践

1. **定期更新**: 每月更新一次cookies
2. **安全保管**: 不要将cookie文件提交到Git
3. **双容器同步**: 确保两个容器都有相同的cookie文件
4. **验证后使用**: 每次更新cookies后都要验证

## 成功标志

当您看到以下信息时，表示cookies工作正常：

```
验证结果:
----------------------------------------
有效: True
已登录: True
详情: {
  "cookies_added": 11,
  "cookies_failed": 0,
  "logout_link_found": true,
  "user_menu_found": true,
  "user_page_accessible": true
}
```

## 支持

如有问题，请检查：
1. Cookie文件格式是否正确
2. 是否复制到了正确的容器
3. 是否运行了修复命令
4. JavDB账号是否正常登录