---
name: dual-subtitle-video
description: Generate lightweight language learning and educational videos with two-tier subtitles (primary focus subtitle in center and context review stream at bottom) from sentence text and audio using Edge-TTS, Pillow, and FFmpeg. Use when asked to create dual-subtitle videos, listening practice videos, educational text-to-video, or vocabulary drills. Fully compatible with publish-video standard payloads and multi-platform publishing. For cinematic narrative videos from articles/documents via NotebookLM, use generate-video instead.
---

# Dual-Subtitle Video Generator

A skill for generating lightweight, high-clarity educational videos featuring a two-tier subtitle layout. The primary subtitle is displayed prominently in the center for active listening focus, while a smaller context stream at the bottom displays preceding, current, and upcoming sentences for easy backtracking and review.

Fully integrated with the `publish-video` workflow, automatically producing standardized video payloads (`payload.md`, `cover.png`, `video.mp4`) ready for publishing across WeChat Official Account Video (`wechat_video`), WeChat Channels (`wechat_channels`), and Bilibili (`bilibili`).

---

## When to Use

Use this skill when:

- Generating listening practice or self-assessment videos from text transcripts.
- Creating dual-tier subtitle videos with central focus text and bottom context streams.
- Converting language lessons, vocabulary drills, or technical presentations into compact MP4 videos without requiring heavy animation or GPU resources.
- Producing educational videos where listeners benefit from reviewing previously spoken sentences without pausing or rewinding.
- Publishing educational videos and dialogues to WeChat Video, WeChat Channels, or Bilibili.

> [!TIP]
> For long-form cinematic narrative or documentary-style AI videos generated from articles or documents via Google NotebookLM, use the `generate-video` skill instead.

---

## Standard Video Payload Specification (`publish-video` 对接规范)

To support multi-platform automated publishing, video assets must follow the standardized payload directory structure:

```text
videos/<topic>/
├── payload.md                     # 视频元数据与发布正文（必须，Frontmatter 严格校验）
├── cover.png                      # 16:9 高清封面（1920x1080，自动生成或自定义）
├── video.mp4                      # 生成的双字幕高清视频（1080p H.264）
└── sentences.txt                  # 原始听力/文本素材（建议归档留存）
```

### `payload.md` 模板与元数据约束

```yaml
---
title: "DevOps 运维工程师日常站会英文听力与对话精练"
author: "Blogger Agent"
desc: "精选 DevOps 运维工程师日常站会与部署排错高频对话，采用双层字幕焦点视窗与上下文流，适合沉浸式英语跟读与自测。"
collection: "软件教程"
cover: "cover.png"
video: "video.mp4"
---

# DevOps 运维工程师日常站会英文听力与对话精练

## 课程简介与学习目标

本期精选 DevOps 运维工程师日常站会与部署排错高频对话，采用双层字幕焦点视窗与上下文流，适合沉浸式英语跟读与自测。

## 对话逐句精析（Transcript）

1. Good morning team, let's start our daily standup.
2. Yesterday, I deployed the new microservice to the staging cluster.
3. Everything passed the smoke tests, so we are ready for production canary.
```

> [!IMPORTANT]
> **发布元数据硬性规范（微信后台与视频号校验）：**
> 1. `title`：**必须为纯文本，严禁包含任何 Emoji 或特殊符号**（如 🇯🇵、🎯、💡 等）。长度建议 ≤ 30 字以内。
> 2. `desc`：长度**严格限制在 60 到 120 字符之间**。过短或过长将导致发布脚本校验失败或被平台拒收。
> 3. `collection`：必须匹配 `blogger.toml` 中配置的 `video_collections`（如 `"软件教程"`, `"程序员"`, `"agent"`）。

---

## Technical Architecture

The generation pipeline relies on decoupled, deterministic stages:

1. **Neural Speech and Timestamp Extraction (Edge-TTS)**:
   Synthesizes speech audio while extracting millisecond-accurate start and end timestamps into a WebVTT cue file.
2. **State-Driven Card Rendering (Pillow)**:
   Each sentence corresponds to a discrete high-resolution 1080p frame card. 30 sentences require rendering only 30 discrete images in memory.
3. **16:9 Cover Image Generation (Pillow)**:
   Renders a 1920x1080 cover matching the video gradient, title card, and badge tags.
4. **Muxing and Fast Encoding (FFmpeg Concat Demuxer)**:
   Assembles the frame images according to their exact cue durations and encodes the final H.264 MP4 video in seconds.
5. **Payload Scaffolding (`payload.md`)**:
   Formats compliant YAML frontmatter and markdown transcript.

---

## UI Layout Specifications

- **Canvas**: 1920x1080 (16:9 Full HD).
- **Background**: Deep navy gradient (`#0B132B` to `#1C2541`) for high contrast and minimal eye fatigue.
- **Top Header Bar**: Topic badge tag (e.g. `DEVOPS ENGLISH`), lesson title, and progress counter (e.g. `05 / 29`).
- **Center Primary Subtitle**:
  - Position: Vertical center (`Y = 400 - 480`).
  - Font: 44pt bold, crisp white (`#FFFFFF`) on dark container card with cyan accent bar.
  - Role: Directly matches the currently spoken audio phrase.
- **Bottom Context Stream**:
  - Position: Near bottom (`Y = 760 - 990`).
  - Font: 23pt - 25pt readable sans-serif.
  - Role: Displays preceding sentence (`◀`, dimmed gray), current sentence (`▶`, highlighted cyan), and next sentence (`…`, preview gray).

---

## Workflow

### 模式 A（推荐分步）：生成标准 Payload ➔ 移交 `publish-video` 发布

#### 步骤 1：生成完整视频 Payload 资产

使用脚本一键生成 `video.mp4`、`cover.png` 及合规的 `payload.md`：

```bash
python3 skills/dual-subtitle-video/scripts/dual_sub_video.py \
  --input videos/devops_standup/sentences.txt \
  --payload-dir videos/devops_standup/ \
  --title "DevOps 运维工程师日常站会英文听力精练" \
  --desc "精选 DevOps 运维工程师日常站会与部署排错高频对话，采用双层字幕焦点视窗与上下文流，适合沉浸式英语跟读与自测。" \
  --collection "软件教程" \
  --tag "DEVOPS ENGLISH"
```

#### 步骤 2：使用 `publish-video` 发布到指定平台

通过 `blogger publish` 发布到指定平台（如微信视频、视频号、B站）：

```bash
# 微信公众号视频消息
python3 -m src.blogger.cli publish \
  --payload videos/devops_standup/payload.md \
  --platform wechat_video

# 微信视频号
python3 -m src.blogger.cli publish \
  --payload videos/devops_standup/payload.md \
  --platform wechat_channels

# B站（支持 --no-publish 预览模式）
python3 -m src.blogger.cli publish \
  --payload videos/devops_standup/payload.md \
  --platform bilibili \
  --no-publish

# 多平台矩阵同时发布
python3 -m src.blogger.cli publish \
  --payload videos/devops_standup/payload.md \
  --platform wechat_video,wechat_channels,bilibili
```

---

### 模式 B（一步到位）：单指令生成并直推目标平台

直接通过 `blogger video` 或脚本参数在生成后立即触发平台发布：

```bash
# 使用 blogger video CLI
python3 -m src.blogger.cli video \
  --type dual-subtitle \
  --payload videos/devops_standup/ \
  --platform wechat_video,wechat_channels,bilibili \
  --title "DevOps 运维工程师日常站会英文听力精练" \
  --desc "精选 DevOps 运维工程师日常站会与部署排错高频对话，采用双层字幕焦点视窗与上下文流，适合沉浸式英语跟读与自测。" \
  --collection "软件教程"
```

---

## CLI Arguments Reference

### `dual_sub_video.py` Arguments

| 参数 | 必选 | 默认值 | 说明 |
|---|---|---|---|
| `-i, --input` | 是 | - | 输入句子文本文件路径（每行一句） |
| `-o, --output` | 否 | - | 单独输出 MP4 文件路径 |
| `--payload-dir` | 否 | - | 输出完整标准视频 Payload 目录（自动生成 `video.mp4`, `cover.png`, `payload.md`） |
| `--cover` | 否 | - | 自定义生成 16:9 封面路径 |
| `--title` | 否 | `English Listening Practice` | 视频标题（纯文本，无 Emoji） |
| `--desc` | 否 | - | 视频简介/摘要（严格 60 ~ 120 字符） |
| `--collection` | 否 | `软件教程` | 平台合集（匹配 `blogger.toml`） |
| `--voice` | 否 | `en-US-JennyNeural` | Edge-TTS 语音音色 |
| `--rate` | 否 | `-6%` | 语速微调（如 `-6%`, `+0%`） |
| `--pitch` | 否 | `+2Hz` | 语调微调 |
| `--tag` | 否 | `LISTENING PRACTICE` | 视频左上角主题 Badge |
| `--subtitle` | 否 | `双字幕沉浸式跟读与听力自测` | 封面上展示的副标题 |
| `--platform` | 否 | - | 生成后直接发布的平台（如 `wechat_video,bilibili`） |
| `--no-publish`| 否 | False | 预览模式（跳过最终发布点击） |

---

## Gotchas and Best Practices

1. **标点与断句**：输入文本的句号、问号和感叹号决定 Edge-TTS 的时间戳切分。确保句子标点规范，避免单行过长（建议每句 8~20 词）。
2. **中文字符字体渲染**：系统已配置 macOS CJK 字体后备（`Hiragino Sans GB` / `STHeiti`），中文标题与副标题均能高清平滑渲染。
3. **发布前自检清单**：
   - [ ] `payload.md` 中的 `desc` 字符数是否在 60 ~ 120 之间。
   - [ ] `title` 是否已剔除所有 Emoji 和特殊字符。
   - [ ] `collection` 是否存在于 `blogger.toml` 中的 `video_collections`。
   - [ ] `cover.png` 是否存在且为 1920x1080 高清图。
