---
name: publish-video
description: Use when the user asks to publish or push a video payload (videos/<topic>/payload.md or directory) to video platforms (WeChat Official Account Video wechat_video, WeChat Channels wechat_channels, Bilibili bilibili), or explicitly uses the /publish-video command. Trigger phrases include "/publish-video", "发布视频", "推送到公众号视频", "推送到视频号", "发布视频到B站", "publish video". Cooperates with generate-video and dual-subtitle-video.
---

# Publish Video Skill

## Overview
This skill takes a completed video payload directory (containing `payload.md`, a clean MP4 video, and a cover image) and executes the `blogger` CLI tool to automatically upload and configure the video draft across configured platforms:
- **`wechat_video`**: WeChat Official Account Video Messages (微信公众号视频素材 / 视频消息, `mp.weixin.qq.com`)
- **`wechat_channels`**: WeChat Channels (微信视频号平台, `channels.weixin.qq.com`)
- **`bilibili`**: Bilibili Creator Studio (哔哩哔哩创作中心, `member.bilibili.com`)

It cooperates directly with upstream video generation workflows (`generate-video` and `dual-subtitle-video`).

---

## Prerequisites（启动前必查）

在执行发布命令之前，**必须**帮用户确认以下几项：

1. **Chrome 必须开启「允许 Apple 事件中的 JavaScript」**（默认关闭）：
   - 操作路径：**Chrome 菜单栏 → View / 查看 → Developer / 开发者 → Allow JavaScript from Apple Events / 允许 Apple 事件中的 JavaScript**，确保已勾选。
2. **目标平台处于登录状态**（只需在 Chrome 中打开对应后台）：
   - `wechat_video`: 任意标签页打开 `https://mp.weixin.qq.com` 且已登录。
   - `wechat_channels`: 任意标签页打开 `https://channels.weixin.qq.com` 且已登录。
   - `bilibili`: 任意标签页打开 `https://member.bilibili.com` 且已登录。
3. **确认 Payload 资产完整**：
   - `payload.md`：包含合法 Front Matter（标题、简介、合集、封面文件名、视频文件名）。
   - 视频文件：优先采用去水印后的 `*_clean.mp4`（若未声明文件名，系统会自动嗅探目录下的 `*_clean.mp4` 或 `*.mp4`）。
   - 封面图片：`cover.png`（若未声明，系统会自动嗅探 `cover.png` / `cover.jpg`）。
4. **macOS 自动化与 Peekaboo 依赖**：
   - 确保系统已安装 `peekaboo`（用于原生系统文件选择对话框与坐标点击）：`which peekaboo`。

---

## Standard Video Payload Specification

每个视频目录推荐遵循如下结构（如 `videos/notebooklm_auth_modes/`）：

```text
videos/<topic>/
├── payload.md                     # 视频元数据与发布正文（必须）
├── cover.png                      # 封面图片（信息图或自定义图）
├── explanation_video.mp4          # 原始视频（可选）
└── explanation_video_clean.mp4    # 去水印后的净版视频（发布首选）
```

### `payload.md` 模板规范

```yaml
---
title: "告别弹窗与重新登录！一文看懂 notebooklm-py 的 [cookies] 静默认证机制"
author: "Gemini CLI"
desc: "本视频直观解析了 notebooklm-py 的两种核心安装与认证机制：[browser] 与 [cookies]。重点剖析了 [cookies] 模式如何利用本地浏览器已登录状态实现静默认证，助你打造优雅的 AI Agent 自动化流。"
collection: "agent"
cover: "cover.png"
video: "explanation_video_clean.mp4"
---

在使用 `notebooklm-py` 打造 Google NotebookLM 自动化工作流时，你是否曾因频繁弹出的 Playwright 认证窗口而感到繁琐？

本期视频将为你彻底解决认证痛点！我们将带你全面对比 `notebooklm-py` 的两种安装/认证模式：

* **常规 `[browser]` 模式**：基于 Playwright 的自动化登录，适合全新环境下的首次授权。
* **黑科技 `[cookies]` 模式（强烈推荐⭐）**：只需通过 `pip install "notebooklm-py[cookies]"` 安装额外依赖，即可实现极客级别的静默认证！

...（完整文案）
```

> **注意：**
> 1. `title`：必须为纯文本，严禁包含任何 Emoji 或特殊符号（微信视频标题校验严格）。
> 2. `desc`：长度必须在 **60 ~ 120 字符** 之间，用于平台推荐摘要与卡片展示。
> 3. `collection`：必须匹配 `blogger.toml` 中配置的 `video_collections`（例如 `agent`, `claude code`, `程序员`, `软件教程` 等）。

---

## Workflow

### 阶段 1：执行发布命令

支持直接指定 `payload.md` 文件或直接传入包含 `payload.md` 的视频目录：

#### 场景 A：发布到微信公众号视频消息（单平台）
```bash
python3 -m src.blogger.cli publish \
  --payload videos/notebooklm_auth_modes/payload.md \
  --platform wechat_video
```

#### 场景 B：发布到微信视频号（单平台）
```bash
python3 -m src.blogger.cli publish \
  --payload videos/notebooklm_auth_modes/payload.md \
  --platform wechat_channels
```

#### 场景 C：发布到 Bilibili（单平台，支持 --no-publish 预览模式）
```bash
python3 -m src.blogger.cli publish \
  --payload videos/notebooklm_auth_modes/payload.md \
  --platform bilibili \
  --no-publish
```

#### 场景 D：多平台矩阵发布（一键推送到三大视频平台）
```bash
python3 -m src.blogger.cli publish \
  --payload videos/notebooklm_auth_modes/payload.md \
  --platform wechat_video,wechat_channels,bilibili
```

---

### 阶段 2：流程监控与异常诊断

**执行时关注终端日志输出：**
- **看到 `WeChat tab not found`**：Chrome 未打开对应登录页面，让用户在 Chrome 中登录一次。
- **看到 `通过 AppleScript 执行 JavaScript 的功能已关闭`**：Prerequisites #1 未开启。
- **看到 `No video file found`**：目录内缺少 MP4 视频，需运行 `watermark-remover` 或检查路径。
- **看到 `Collection 'xxx' not in allowed video_collections`**：检查 `blogger.toml` 并更正 `collection`。

---

### 阶段 3：收尾清单与用户汇报

脚本运行完成后，必须给用户呈现发布核验清单：

```
✓ / ✗ 视频文件上传（检查后台是否成功载入视频）
✓ / ✗ 视频标题注入（检查是否包含特殊字符）
✓ / ✗ 视频封面设置（检查 cover.png 是否成功裁切/应用）
✓ / ✗ 简介/文案注入（检查正文或简介框）
✓ / ✗ 原创声明与声明确认（已自动勾选）
✓ / ✗ 合集设置（匹配 blogger.toml video_collections）
✓ / ✗ 保存为草稿（已自动点击保存草稿）
```
