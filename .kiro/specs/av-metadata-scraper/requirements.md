# Requirements Document

## Introduction

本项目旨在开发一个自动化的日本AV影片元数据刮削和整理系统，通过Docker容器部署。系统能够从多个知名网站（如javdb、javlibrary等）自动获取影片的详细信息，包括标题、演员、封面图、海报等元数据，并根据获取的信息自动整理本地视频文件到指定的目录结构中。

## Requirements

### Requirement 1

**User Story:** 作为用户，我希望系统能够自动扫描指定目录下的所有视频文件，以便识别需要处理的影片文件

#### Acceptance Criteria

1. WHEN 系统启动时 THEN 系统 SHALL 扫描用户配置的源目录下的所有视频文件
2. WHEN 发现视频文件时 THEN 系统 SHALL 支持常见的视频格式（mp4, mkv, avi, wmv, mov等）
3. WHEN 扫描完成时 THEN 系统 SHALL 记录找到的视频文件数量和路径信息
4. IF 目录中存在子目录 THEN 系统 SHALL 递归扫描所有子目录

### Requirement 2

**User Story:** 作为用户，我希望系统能够从多个网站刮削影片元数据，以便获取完整准确的影片信息

#### Acceptance Criteria

1. WHEN 系统处理视频文件时 THEN 系统 SHALL 从javdb网站获取元数据
2. WHEN javdb获取失败时 THEN 系统 SHALL 尝试从javlibrary网站获取元数据
3. WHEN 刮削元数据时 THEN 系统 SHALL 获取影片标题、演员名称、发行日期、制作商、封面图、海报图等信息
4. IF javdb需要登录 THEN 系统 SHALL 使用用户提供的账号密码自动登录
5. WHEN 遇到图像验证码时 THEN 系统 SHALL 能够处理或绕过验证码验证

### Requirement 3

**User Story:** 作为用户，我希望系统能够自动处理登录状态和Cookie管理，以便实现无人值守的自动化运行

#### Acceptance Criteria

1. WHEN 系统启动时 THEN 系统 SHALL 自动检查登录状态
2. WHEN Cookie过期时 THEN 系统 SHALL 自动刷新登录状态
3. WHEN 需要登录时 THEN 系统 SHALL 模拟浏览器行为进行登录
4. IF 登录失败 THEN 系统 SHALL 记录错误并尝试重新登录
5. WHEN 系统运行时 THEN 系统 SHALL 定时检查和维护登录状态

### Requirement 4

**User Story:** 作为用户，我希望系统能够根据刮削到的元数据自动整理视频文件，以便按照规范的目录结构存储影片

#### Acceptance Criteria

1. WHEN 获取到完整元数据时 THEN 系统 SHALL 按照"演员名/番号名称/番号名称.扩展名"的格式整理文件
2. WHEN 存在多个演员时 THEN 系统 SHALL 使用主演或第一个演员作为目录名
3. WHEN 目标目录不存在时 THEN 系统 SHALL 自动创建相应的目录结构
4. IF 目标位置已存在同名文件 THEN 系统 SHALL 提供重命名或跳过的处理策略
5. WHEN 文件移动完成时 THEN 系统 SHALL 验证文件完整性

### Requirement 5

**User Story:** 作为用户，我希望系统能够保存刮削到的元数据，以便后续查看和管理影片信息

#### Acceptance Criteria

1. WHEN 刮削到元数据时 THEN 系统 SHALL 将元数据保存为JSON或XML格式的文件
2. WHEN 下载封面图和海报时 THEN 系统 SHALL 将图片保存到对应的影片目录中
3. WHEN 保存元数据时 THEN 系统 SHALL 包含刮削时间、数据源等附加信息
4. IF 元数据文件已存在 THEN 系统 SHALL 提供更新或跳过的选项

### Requirement 6

**User Story:** 作为用户，我希望系统能够通过Docker容器部署，以便简化安装和配置过程

#### Acceptance Criteria

1. WHEN 用户部署系统时 THEN 系统 SHALL 提供完整的Docker镜像
2. WHEN 容器启动时 THEN 系统 SHALL 支持通过环境变量配置关键参数
3. WHEN 运行容器时 THEN 系统 SHALL 支持挂载本地目录作为源目录和目标目录
4. IF 需要持久化配置 THEN 系统 SHALL 支持配置文件的外部挂载

### Requirement 7

**User Story:** 作为用户，我希望系统能够提供日志记录和错误处理，以便监控系统运行状态和排查问题

#### Acceptance Criteria

1. WHEN 系统运行时 THEN 系统 SHALL 记录详细的操作日志
2. WHEN 发生错误时 THEN 系统 SHALL 记录错误信息和堆栈跟踪
3. WHEN 刮削失败时 THEN 系统 SHALL 记录失败原因并继续处理其他文件
4. IF 系统异常退出 THEN 系统 SHALL 保存当前处理进度以便恢复

### Requirement 8

**User Story:** 作为用户，我希望系统能够支持配置和自定义，以便根据个人需求调整系统行为

#### Acceptance Criteria

1. WHEN 用户配置系统时 THEN 系统 SHALL 支持配置刮削网站的优先级
2. WHEN 用户设置参数时 THEN 系统 SHALL 支持配置文件命名规则
3. WHEN 系统运行时 THEN 系统 SHALL 支持配置并发处理的文件数量
4. IF 用户需要代理 THEN 系统 SHALL 支持HTTP/HTTPS代理配置