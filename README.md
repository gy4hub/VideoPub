# VideoPub

当前版本：`1.1.0`

> 多平台视频发布自动化工具 — 一次操作，同步发布到微信视频号、抖音、Bilibili、YouTube

---

## 功能特性

- 📄 **多格式元数据**：支持 JSON、Markdown (.md)、TXT、Word (.docx)、PDF，字段名支持中英文
- 🚀 **四平台发布**：微信视频号 / 抖音（Playwright）· Bilibili（biliup API）· YouTube（Data API v3）
- 🔁 **幂等重发**：已完成的平台自动跳过，`.status/` 文件夹记录每个平台状态
- 👀 **文件夹监控**：`watch` 命令监控目录，新视频自动触发上传
- 📝 **首评自动发布**：上传成功后自动发布第一条评论
- 🗓️ **定时发布**：支持各平台的定时发布时间设置
- 📋 **结构化日志**：loguru 控制台彩色输出 + 按日轮转日志文件
- 🔄 **重试机制**：可配置重试次数和指数退避延迟
- 🍎 **macOS 守护进程**：一键安装为 launchd 服务，开机自动运行

---

## 1.1.0

- 新增 `metadata.md` 和 `metadata.txt` 支持
- 纯文本元数据与 Word / PDF 共用同一套 `key: value` + `[platform]` 语法
- 元数据查找优先级更新为 `JSON > MD > TXT > DOCX > PDF`

## Unreleased

- 新增 `videopub-mcp`，可将 VideoPub 作为本地 MCP server 通过 stdio 暴露给 AI 工具调用
- MCP tools 首批封装：版本查询、支持平台查询、文件夹解析、文件夹上传、平台登录、登录状态检查、文件夹状态读取

## 1.0.0 正式版

- 已完成 `wechat`、`douyin`、`bilibili`、`youtube` 四平台真实发布联调
- 已验证登录态复用、封面处理、合集选择、定时发布和最终发布动作
- Playwright 平台的关键页面流程已按真实页面收敛，不再依赖大量无效兜底步骤
- 封面生成已按平台分流：视频号 `3:4`、抖音 `3:4/4:3`、YouTube 专用横版
- 推荐发布前先在小样本文件夹做单平台验证，再切到正式素材批量使用

---

## 安装

### 前置要求

- Python ≥ 3.11
- macOS（launchd 部署）或任意 POSIX 系统（手动运行）

### 安装步骤

```bash
git clone <repo-url>
cd VideoPub

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .

# 安装 Playwright 浏览器
playwright install chromium
```

---

## 快速开始

### 1. 准备发布文件夹

```
my_video/
├── video.mp4           # 视频文件（支持 .mp4 .mov .avi .mkv）
├── cover.jpg           # 封面图（支持 .jpg .png .webp）
└── metadata.json       # 元数据文件（也支持 metadata.md/.txt/.docx/.pdf）
```

封面处理规则：

- 默认优先使用文件名包含 `cover` 或 `封面` 的图片
- 如果封面原图已经是横版，直接使用原图
- 如果封面原图是竖版，系统会先生成一张 `__portrait_safe.jpg` 竖版安全图，给文字留出安全边距
- 对需要横封面的平台，系统会再基于安全图生成一张 `__landscape.jpg` 横版图
- `youtube` 会单独生成一张不额外出血的 `__youtube_landscape.jpg`
- 生成后的安全图和横版图都会放回原封面所在文件夹，不会写到隐藏目录
- `bilibili`、`youtube`、`douyin` 会优先使用自动生成的横版图
- `wechat` 会优先使用自动生成的 `3:4` 专用封面，并通过页面里的封面编辑流程上传

### 2. 编写 metadata.json

```json
{
  "platforms": [
    {
      "platform": "bilibili",
      "title": "【科研干货】磁珠纯化的三大常见误区",
      "description": "本期视频详细讲解磁珠纯化技术中最容易踩的三个坑...",
      "tags": ["磁珠", "纯化技术", "科研"],
      "category": "201",
      "first_comment": "你们实验室用的什么品牌的磁珠？来评论区聊聊！"
    },
    {
      "platform": "youtube",
      "title": "3 Common Mistakes in Magnetic Bead Purification",
      "description": "In this video, we cover the three most common pitfalls...",
      "tags": ["magnetic beads", "purification", "laboratory"],
      "scheduled_time": "2026-04-03T20:00:00"
    },
    {
      "platform": "抖音",
      "title": "磁珠纯化的三大误区",
      "description": "手把手教你避开这三个坑",
      "tags": ["磁珠", "实验技巧"],
      "first_comment": "关注我，获取更多科研干货！"
    },
    {
      "platform": "视频号",
      "title": "磁珠纯化常见误区详解",
      "short_title": "磁珠纯化误区",
      "description": "磁珠纯化技术解析...",
      "tags": ["磁珠纯化", "实验室"],
      "is_original": true
    }
  ]
}
```

### 3. 或使用 Markdown / TXT / Word / PDF（支持中文字段名）

```
视频路径: video.mp4
封面路径: cover.jpg

[bilibili]
标题: 磁珠纯化的三大常见误区
简介: 本期视频详细讲解...
标签: 磁珠, 纯化技术, 科研
分类: 201
首评: 你们实验室用的什么品牌的磁珠？

[youtube]
标题: 3 Common Mistakes in Magnetic Bead Purification
描述: In this video...
标签: magnetic beads, purification
定时发布: 2026-04-03 20:00

[抖音]
标题: 磁珠纯化的三大误区
描述: 手把手教你避开这三个坑
标签: 磁珠, 实验技巧
```

`metadata.md` 和 `metadata.txt` 与 Word / PDF 使用同样的 KV 文本语法，最适合版本管理和快速编辑。

如果你的封面是竖图，例如 `封面.jpg`，上传前可能会自动在同目录生成：

```text
封面__portrait_safe.jpg
封面__landscape.jpg
```

前者是竖版安全图，后者是横版图，都是上传时自动生成的中间产物，可以保留。

### 4. 登录各平台

```bash
# 首次使用前需要登录各平台（只需一次）
videopub login bilibili   # 扫描二维码登录
videopub login youtube    # 弹出浏览器完成 OAuth
videopub login douyin     # 弹出浏览器扫码
videopub login wechat     # 弹出浏览器扫码

# 查看登录状态
videopub status
```

### 5. 发布视频

```bash
# 发布到所有平台
videopub upload my_video/

# 只发布到指定平台
videopub upload my_video/ -p bilibili -p youtube

# 显示详细日志
videopub --verbose upload my_video/
```

---

## 文件夹监控

自动监控目录，新增视频文件夹时自动发布：

```bash
# 监控 ~/videos 目录
videopub watch ~/videos

# 只监控并发布到特定平台
videopub watch ~/videos -p bilibili -p youtube
```

**触发条件**：子目录同时包含视频文件（.mp4/.mov 等）和元数据文件（metadata.json/.md/.txt/.docx/.pdf）

---

## MCP Server

VideoPub 现在可以作为一个本地 MCP server 运行，默认使用 `stdio` transport。

安装依赖后可直接启动：

```bash
videopub-mcp
```

当前封装的 MCP tools：

- `get_version`
- `get_supported_platforms`
- `parse_folder`
- `upload_folder`
- `login_platform`
- `get_login_status`
- `get_folder_status`

如果你要把它接到支持 MCP 的客户端，命令通常可以直接写成：

```json
{
  "mcpServers": {
    "videopub": {
      "command": "videopub-mcp"
    }
  }
}
```

---

## 状态文件

每次上传后，在视频文件夹内生成 `.status/<platform>.json`：

```json
{
  "platform": "bilibili",
  "state": "done",
  "updated_at": "2026-04-03T20:15:32",
  "video_id": "BV1xx411c7XY",
  "video_url": "https://www.bilibili.com/video/BV1xx411c7XY"
}
```

状态值：`pending` → `uploading` → `done` / `error`

已标记为 `done` 的平台在重新运行时会自动跳过（幂等）。

---

## 配置文件

### 全局配置 `videopub/config/settings.yaml`

```yaml
watch_folder: ~/videopub/watch_folder
log_dir: ~/videopub/logs
upload_timeout: 600

browser:
  headless: true
  slow_mo: 100

retry:
  max_attempts: 3
  delay_seconds: 30
  backoff_factor: 2.0
```

### Bilibili `videopub/config/platforms/bilibili.yaml`

```yaml
cookie_path: ~/.videopub/bilibili_cookie.json
default_tid: 201  # 科学科普
```

### YouTube `videopub/config/platforms/youtube.yaml`

```yaml
oauth_client_secrets: ~/.videopub/youtube_client_secrets.json
token_path: ~/.videopub/youtube_token.json
default_privacy: unlisted
default_category: "28"  # Science & Technology
```

### 抖音 `videopub/config/platforms/douyin.yaml`

```yaml
cookie_path: ~/.videopub/douyin_cookie.json
```

### 微信视频号 `videopub/config/platforms/wechat.yaml`

```yaml
cookie_path: ~/.videopub/wechat_cookie.json
login_timeout: 120
default_original: true
```

---

## macOS 后台服务（launchd）

将 `videopub watch` 安装为开机自启的 launchd 服务：

```bash
# 安装（自动读取 settings.yaml 中的 watch_folder）
bash deploy/install.sh

# 或指定监控目录
bash deploy/install.sh ~/my_watch_folder

# 查看服务状态
launchctl list | grep videopub

# 查看日志
tail -f ~/videopub/logs/launchd_stderr.log

# 卸载
bash deploy/uninstall.sh
```

---

## YouTube 认证设置

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目，启用 **YouTube Data API v3**
3. 创建 OAuth 2.0 客户端凭据（桌面应用）
4. 下载 `client_secrets.json` 保存至 `~/.videopub/youtube_client_secrets.json`
5. 运行 `videopub login youtube` 完成授权

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=videopub --cov-report=term-missing
```

### 项目结构

```
videopub/
├── cli.py                     # CLI 入口（click）
├── logging_config.py          # loguru 日志配置
├── core/
│   ├── models.py              # Pydantic 数据模型
│   ├── metadata_parser.py     # JSON / Markdown / TXT / Word / PDF 解析
│   ├── config_loader.py       # YAML 配置加载
│   ├── orchestrator.py        # 发布调度器
│   ├── status.py              # .status 文件管理
│   └── retry.py               # 重试装饰器
├── uploaders/
│   ├── base.py                # 抽象基类
│   ├── browser_base.py        # Playwright 管理器
│   ├── bilibili/              # biliup API
│   ├── youtube/               # Google Data API v3
│   ├── douyin/                # Playwright 自动化
│   └── wechat/                # Playwright 自动化
└── config/
    ├── settings.yaml
    └── platforms/
        ├── bilibili.yaml
        ├── douyin.yaml
        ├── wechat.yaml
        └── youtube.yaml
deploy/
├── com.videopub.watch.plist   # launchd plist 模板
├── install.sh                 # 安装脚本
└── uninstall.sh               # 卸载脚本
tests/
├── test_cli.py
├── test_models.py
├── test_metadata_parser.py
├── test_docx_pdf_parser.py
├── test_orchestrator.py
├── test_status.py
└── test_e2e.py
```

---

## License

MIT
