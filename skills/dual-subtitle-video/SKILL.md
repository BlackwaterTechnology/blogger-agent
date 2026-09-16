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
title: "DevOps Daily Standup English Listening Practice"
author: "Blogger Agent"
desc: "Practice daily DevOps standup English with dual-tier subtitles and live context stream for immersive listening."
collection: "软件教程"
cover: "cover.png"
video: "video.mp4"
---

# DevOps Daily Standup English Listening Practice

## Overview & Learning Objectives

Master essential DevOps daily standup and deployment troubleshooting conversations with dual-tier subtitles and context streaming.

## Sentence-by-Sentence Transcript

1. Good morning team, let's start our daily standup.
2. Yesterday, I deployed the new microservice to the staging cluster.
3. Everything passed the smoke tests, so we are ready for production canary.
```

> [!IMPORTANT]
> **发布元数据硬性规范（全英文标准与平台校验）：**
> 1. `title`：**必须为纯英文文本（Title Case），严禁包含任何 Emoji 或特殊符号**（如 🇯🇵、🎯、💡 等）。长度建议在 30 ~ 60 字符以内。
> 2. `desc`：**必须为纯英文**，长度**严格限制在 60 到 120 字符之间**。过短或过长将导致发布脚本校验失败或被平台拒收。
> 3. `cover`：封面主标题、副标题（默认 `Dual-Subtitle Immersion & Shadowing Drill`）与 Badge 必须全部采用英文。
> 4. `collection`：必须匹配 `blogger.toml` 中配置的 `video_collections`（如 `"软件教程"`, `"程序员"`, `"agent"`）。

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
  --title "DevOps Daily Standup English Listening Practice" \
  --desc "Practice daily DevOps standup English with dual-tier subtitles and live context stream for immersive listening." \
  --collection "软件教程" \
  --tag "DEVOPS ENGLISH" \
  --subtitle "Dual-Subtitle Immersion & Shadowing Drill"
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
  --title "DevOps Daily Standup English Listening Practice" \
  --desc "Practice daily DevOps standup English with dual-tier subtitles and live context stream for immersive listening." \
  --collection "软件教程"
```

---

## CLI Arguments Reference

### `dual_sub_video.py` Arguments

| 参数 | 必选 | 默认值 | 说明 |
|---|---|---|---|
| `-i, --input` | 是 | - | 输入句子文本文件路径（每行一句英文） |
| `-o, --output` | 否 | - | 单独输出 MP4 文件路径 |
| `--payload-dir` | 否 | - | 输出完整标准视频 Payload 目录（自动生成 `video.mp4`, `cover.png`, `payload.md`） |
| `--cover` | 否 | - | 自定义生成 16:9 封面路径 |
| `--title` | 否 | `English Listening Practice` | 英文视频标题（纯英文文本，Title Case，无 Emoji） |
| `--desc` | 否 | 自动生成英文摘要 | 英文视频简介/摘要（严格 60 ~ 120 字符） |
| `--collection` | 否 | `软件教程` | 平台合集（匹配 `blogger.toml`） |
| `--voice` | 否 | `en-US-JennyNeural` | Edge-TTS 语音音色 |
| `--rate` | 否 | `-6%` | 语速微调（如 `-6%`, `+0%`） |
| `--pitch` | 否 | `+2Hz` | 语调微调 |
| `--tag` | 否 | `LISTENING PRACTICE` | 视频左上角英文主题 Badge |
| `--subtitle` | 否 | `Dual-Subtitle Immersion & Shadowing Drill` | 封面上展示的英文副标题 |
| `--platform` | 否 | - | 生成后直接发布的平台（如 `wechat_video,bilibili`） |
| `--no-publish`| 否 | False | 预览模式（跳过最终发布点击） |

---

## English-First Quality Standard (Title, Cover, Description)

1. **专长定位与语言一致性**：`dual-subtitle-video` 专门服务于英语学习与听力自测场景，因此所有对外展现的元数据（标题、封面卡片文案、简介摘要、Payload 正文目录）必须统一采用**纯英文**。
2. **标题规范（Title）**：
   - 必须采用英文 Title Case，如 `DevOps Daily Standup English Listening Practice`。
   - 严禁包含任何 Emoji 或特殊装饰符号（避免平台接口拒绝）。
   - 长度建议在 30 ~ 60 字符以内。
3. **封面卡片规范（Cover Art）**：
   - 主标题：居中大卡片展示英文标题。
   - 副标题：默认英文 `Dual-Subtitle Immersion & Shadowing Drill`（或自定义英文说明）。
   - 顶部 Badge：纯英文全大写（如 `LISTENING PRACTICE`, `TECH TALK`）。
   - 底部元信息：已内置 `1080P FULL HD | DUAL-SUBTITLE STREAM`。
4. **简介摘要规范（Description）**：
   - 必须为纯英文，且字符数严格控制在 **60 ~ 120 字符** 之间。
   - 自动补全机制已内置英文描述模版，杜绝中文文本混入英文视频元数据。
5. **发布前自检清单**：
   - [ ] `title` 是否为纯英文 Title Case，无 Emoji 与特殊字符。
   - [ ] `cover.png` 上的标题与副标题是否全部为英文。
   - [ ] `payload.md` 中的 `desc` 是否为英文且字符数在 60 ~ 120 之间。
   - [ ] `collection` 是否存在于 `blogger.toml` 中的 `video_collections`。
