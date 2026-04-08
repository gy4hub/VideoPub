# Changelog

## Unreleased

- 新增 `videopub-mcp` MCP server 封装
- 支持 `stdio`、`sse`、`streamable-http` transport
- 暴露版本查询、平台查询、目录校验、可发布目录发现、文件夹解析、上传执行、平台登录、登录状态、配置读取和状态文件读取工具

## 1.1.0 - 2026-04-08

- 新增 `metadata.md` 和 `metadata.txt` 元数据支持
- 主解析器恢复为正式实现，并统一支持 JSON / Markdown / TXT / Word / PDF
- 纯文本元数据与 Word / PDF 共用同一套 `key: value` + `[platform]` 解析规则
- 元数据查找优先级更新为 `JSON > MD > TXT > DOCX > PDF`
- README、CLI 版本输出和测试同步升级到 `1.1.0`

## 1.0.0 - 2026-04-05

- 完成 `wechat`、`douyin`、`bilibili`、`youtube` 四平台真实发布联调
- 修复微信视频号封面入口、封面编辑弹层识别、合集选择、定时发布和发表确认
- 修复抖音封面上传、横竖封面流程、合集选择、标签收尾和真实发布确认
- 修复 Bilibili 登录态兼容、投稿提交、定时发布时间和封面处理
- 修复 YouTube OAuth 上传、定时时区处理、缩略图 MIME 类型和专用横版封面
- 支持按平台生成专用封面中间图，并回写到原素材目录
- 将项目版本提升为 `1.0.0`
