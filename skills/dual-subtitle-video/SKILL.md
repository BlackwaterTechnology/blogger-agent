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
├── cover.png                      # 16:9 高清封面（1920x1080，与视频共享氛围底图）
├── video.mp4                      # 生成的双字幕高清视频（1080p H.264）
├── sentences.txt                  # 原始听力/文本素材（建议归档留存）
└── bg.png                         # 氛围主题底图（可选，自动用于高斯模糊与暗色蒙版）
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
- **Background**: 
  - **Ambient Theme Backdrop（推荐）**: 单张主题插图经 Aspect-Fill 智能裁剪，叠加 **`3px` 电影级微景深高斯模糊**与 **`20%` 深海蓝蒙版（`#0B132B`，`alpha=0.20`）**。在保留插画丰富细节、色彩饱满度与温暖光影的同时，通过微景深将实色字幕卡片自然衬托立体浮现，彻底告别画面发灰过淡。
  - **Fallback**: 未指定背景图时，平滑降级为深曜黑蓝线性渐变（`#0B132B` 至 `#1C2541`）。
- **Top Header Bar**: Topic badge tag (e.g. `DEVOPS ENGLISH`), lesson title, and progress counter (e.g. `05 / 29`).
- **Center Primary Subtitle**:
  - Position: Vertical center (`Y = 400 - 480`).
  - Font: 44pt bold, crisp white (`#FFFFFF`) on dark container card with cyan accent bar.
  - Role: Directly matches the currently spoken audio phrase.
- **Bottom Context Stream**:
  - Position: Near bottom (`Y = 760 - 990`).
  - Label: Dynamic capsule badge labeled `CONTEXT STREAM` (pure English, strictly zero Chinese).
  - Font: 23pt - 25pt readable sans-serif.
  - Role: Displays preceding sentence (`◀`, dimmed gray), current sentence (`▶`, highlighted cyan), and next sentence (`…`, preview gray).

---

## Ambient Backdrop Standard & Sourcing Strategy (氛围底图规范与双轨生成策略)

为了兼顾视听体验的沉浸感与学习工具的阅读专注度，采用**“强氛围、弱干扰、细节生动”**设计，支持根据主题特性的双轨生图策略：

### 1. 职场、生活与社论场景 ➔ Agent Function (`generate_image`)
适用于商务会议、机场出行、咖啡馆点餐、面试英语等具备真实空间感的话题。
- **生图标准**：遵循杂志社论艺术风格（Modern Editorial Flat Vector 或 Isometric Diorama），**坚决杜绝发光蓝脑、机械手、乱码字符与人物正脸**。
- **顶部留白铁律**：Prompt **必须显式声明 `clean dark negative space at the top, no text`**，确保图片上部区域纯净深色，避免 AI 绘制杂乱按钮或伪文字导致与顶部标题栏文字重叠冲突。
- **实色容器保护原则（Solid Container Protection）**：中央主字幕采用 `#1E293B` 实色圆角卡片，底部上下文采用 `#0F172A` 实色卡片，文字自带天然高对比度隔离屏障。因此背景处理**严禁重度高斯模糊与暴力压暗**，统一采用默认微景深（`blur=3`）与低度蒙版（`alpha=0.20`），实现画质细节与文本可读性的双重极致。
- **Prompt 范式**：
  > *"Modern editorial vector illustration of a cozy open-plan tech startup office in the morning, soft warm sunlight streaming through large glass windows, minimal laptops on wooden desks, clean muted slate navy and warm amber color palette, clean dark negative space at the top, flat design, sophisticated art magazine style, no text, no characters' faces."*
- **生成后操作**：保存为 `videos/<topic>/bg.png`，渲染时自动被检测并应用电影级微景深与微光蒙版。

### 2. 硬核技术、架构与开发场景 ➔ 原生 SVG 弥散光斑 (`generate_ambient_svg`)
适用于 Linux、K8s、数据库、系统底层等偏极客话题。
- **生成方式**：无需外部 API，直接调用内置 `generate_ambient_svg` 生成包含青色/靛蓝/翡翠绿大弥散光球（Mesh Blobs）及 Blueprint 科技网格的 SVG，经 `sips -s format png --resampleWidth 1920` 秒级导出为 `bg.png`。
- **特点**：零 API 成本、纯本地秒级生成、100% 确定性。

### 3. 约定优于配置（Convention over Configuration）
- 只要 Payload 目录存在 `bg.png` 或 `background.png`，脚本自动启用作为背景；
- 导出的 `cover.png` 自动复用同款氛围背景，确保视频封画风格完全一致。

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
| `--level` | 否 | `a2` | CEFR 英语分级（`a2`, `b1`, `b2`, `c1`；默认 `a2`，自动联动语速与 Badge） |
| `--rate` | 否 | 联动 level（A2为 `-12%`） | 语速微调（若手动指定则覆盖 level 预设，如 `-12%`, `-6%`, `+0%`） |
| `--pitch` | 否 | `+2Hz` | 语调微调 |
| `--tag` | 否 | 联动 level（A2为 `A2 · ELEMENTARY`） | 视频左上角英文主题 Badge（自定义文本将自动附加级别前缀） |
| `--subtitle` | 否 | 联动 level（A2为 `CEFR A2 Elementary · Slow & Clear Drill`） | 封面上展示的英文副标题 |
| `--bg-image` | 否 | 自动检测 `bg.png` | 自定义氛围主题背景图片路径（经高斯模糊与暗色蒙版后呈现） |
| `--platform` | 否 | - | 生成后直接发布的平台（如 `wechat_video,bilibili`） |
| `--no-publish`| 否 | False | 预览模式（跳过最终发布点击） |

---

## CEFR English Difficulty Standards (英语分级规范与 Agent 素材创作标准)

为了确保听力与跟读训练符合**“可理解性输入（Comprehensible Input / i+1）”**的认知规律，本 Skill 严格以国际标准 **CEFR（欧洲共同语言参考标准）** 为基准建立分级与参数联动：

### 1. 四级分级矩阵（默认：A2）

| CEFR 级别 | 目标受众与场景 | 词汇量基准 | 建议单句长度 | 默认语速 (`--rate`) | 默认 Header Badge | 默认封面副标题 |
|---|---|---|---|---|---|---|
| **A2** (默认) | **基础入门 / 慢速精听**<br>日常打招呼、极简命令、生存口语 | ~1,500 词 | 6 ~ 10 词 | `-12%` | `A2 · ELEMENTARY` | `CEFR A2 Elementary · Slow & Clear Drill` |
| **B1** | **进阶实用 / 职场通用**<br>通用工作流沟通、邮件回复、需求讨论 | ~3,000 词 | 10 ~ 16 词 | `-6%` | `B1 · INTERMEDIATE` | `CEFR B1 Intermediate · Workplace Listening` |
| **B2** | **职场实战 / 专业流利**<br>DevOps 站会、故障排查、架构选型、面试 | ~5,000 词 | 14 ~ 22 词 | `-3%` | `B2 · PROFESSIONAL` | `CEFR B2 Professional · Fluent Immersion` |
| **C1** | **母语级实战 / 高阶沉浸**<br>开源峰会演讲、技术哲学、复杂争辩 | 8,000+ 词 | 18 ~ 30 词 (复合长句) | `+0%` (自然常速) | `C1 · ADVANCED` | `CEFR C1 Advanced · Native Pace Shadowing` |

### 2. 参数自动联动机制
- **零配置开箱即用**：传入 `--level a2`（或默认缺省）时，引擎自动将 Edge-TTS 语速调至 `-12%`，顶部 Header 自动设为 `A2 · ELEMENTARY`，封面副标题自动设为 `CEFR A2 Elementary · Slow & Clear Drill`。
- **自定义 Tag 智能前缀**：若用户指定 `--tag "DEVOPS"`，系统会自动规范化为 `A2 · DEVOPS`，确保难度标签始终在移动端可视区域清晰可见。
- **手动覆盖**：如果显式指定了 `--rate` 或 `--tag`，以用户手动指定的参数为准。

### 3. Agent 素材创作铁律（当 Agent 负责起草 `sentences.txt` 时）
1. **未指定级别时，默认按 A2 编写**：
   - 句子结构采用主谓宾（SVO），避免多层嵌套从句；
   - 优先使用常见动词（get, run, check, fix, send）与高频技术词；
   - 每句话控制在 6 ~ 10 个英文单词，杜绝单行超过 14 个词。
2. **专业话题推荐升阶**：
   - 如果用户明确指定是“架构师面试”、“线上重大故障排查”等高阶话题，Agent 应主动建议或指定 `--level b2`。

---

## English-First Quality Standard (Title, Cover, Description)

1. **专长定位与语言一致性**：`dual-subtitle-video` 专门服务于英语学习与听力自测场景，因此所有对外展现的元数据（标题、封面卡片文案、简介摘要、Payload 正文目录）必须统一采用**纯英文**。
2. **标题规范（Title）**：
   - 必须采用英文 Title Case，如 `DevOps Daily Standup English Listening Practice`。
   - 严禁包含任何 Emoji 或特殊装饰符号（避免平台接口拒绝）。
   - 长度建议在 30 ~ 60 字符以内。
3. **封面卡片规范（Cover Art）**：
   - 主标题：居中大卡片展示英文标题。
   - 副标题：默认英文 `CEFR A2 Elementary · Slow & Clear Drill`（自动随 level 联动，或自定义英文说明）。
   - 顶部 Badge：纯英文全大写带级别标识（如 `A2 · ELEMENTARY`, `B2 · DEVOPS`）。
   - 底部元信息：已内置 `1080P FULL HD | DUAL-SUBTITLE STREAM`。
4. **简介摘要规范（Description）**：
   - 必须为纯英文，且字符数严格控制在 **60 ~ 120 字符** 之间。
   - 自动补全机制已内置英文描述模版，杜绝中文文本混入英文视频元数据。
5. **视频内画面全英文铁律（Zero Chinese on Video Frames）**：
   - 视频画面内部所有元素（顶部 Badge、标题、进度指示、中央主字幕、底部 `CONTEXT STREAM` 标签及前后回顾句）必须**100% 保持纯英文**。
   - 严禁在底部容器或画面任何角落出现任何中文标签（如旧版的“/ 上下文回顾”），确保纯正的沉浸式英语学习环境与高水准国际化交付质感。
6. **发布前自检清单**：
   - [ ] 视频画面内所有标签（包括底部 `CONTEXT STREAM`）是否为 100% 纯英文，严格无中文。
   - [ ] `level` 是否匹配目标受众（默认为 `a2`，若为深度技术讨论建议 `b2`）。
   - [ ] `title` 是否为纯英文 Title Case，无 Emoji 与特殊字符。
   - [ ] `cover.png` 上的标题与副标题是否全部为英文。
   - [ ] `payload.md` 中的 `desc` 是否为英文且字符数在 60 ~ 120 之间。
   - [ ] `collection` 是否存在于 `blogger.toml` 中的 `video_collections`。
