---
name: blogger-agent
description: 多平台文章自动化发布 skill。当用户需要写文章、分享经验、或发布内容到博客平台（微信公众号、掘金、CSDN等）时触发。此 skill 会优化文章结构、生成标题和插图（使用 PlantUML 或 Canva），生成特定格式的 Markdown 并利用 Python CLI 工具自动将文章草稿发布到目标平台。
---

# Blogger Agent

## Overview

将任意输入内容（文章草稿、对话、观点、代码笔记等）转化为结构完整的技术文章，自动生成插图和封面，并调用本地工具自动推送到各大主流博客平台（目前已支持微信公众号，后续将扩展掘金、CSDN 等）。

与纯界面的浏览器自动化不同，此 skill 使用的是封装好的 `blogger` CLI 工具，Agent 只需准备好标准的 Payload 目录即可，无需手动逐步控制浏览器 UI。

## Required Tools/Servers

执行此 skill 需要以下能力：

- **bash**: 用于运行 Python 发布脚本和子进程图片生成。
- **文件系统**: 用于创建 Payload 目录、保存生成的图片和 Markdown。

### 图片生成

图片生成采取 **AI 设计优先，Text-to-Diagram 兜底** 的策略。如果 Agent 原生支持图片生成，直接生成高质量图片。若不支持，则集成基于 Kroki 的文本转图能力，保证零外部依赖也能生成配图：

```
主 Agent
    │
    ├─ 编写 Mermaid/PlantUML 代码 → 调用 generate-diagram (MCP 或 CLI)
    │                                     │
    │                                     └─ 通过 Kroki 渲染并保存到 payload 目录
    │
    └─ 生成 Payload 目录 → 调用 publish_article (MCP) 或 blogger publish (CLI)
```

支持两种调用模式：
1. **MCP 模式**：直接调用服务端暴露的 `generate_diagram` 工具。
2. **CLI 模式**：通过终端执行 `blogger generate-diagram --type mermaid --input xxx --output yyy`。

## Workflow

```
用户输入 (写文章请求)
    ↓
Step 1: 内容分析与优化
    ↓
Step 2: 封面与插图生成 (必填)
    ↓
Step 3: 构造 Payload 目录
    ↓
Step 4: 执行发布脚本
```

### Step 1: 内容分析与专业化创作 (Professional Content Creation)

基于用户输入，运用专业的内容创作方法论，撰写高水准的技术/观点文章：

1. **结构设计 (Structure)**：采用经典的“钩子引题(Hook) -> 痛点分析(Pain Point) -> 核心方案/观点(Solution) -> 总结升华(Takeaway)”逻辑闭环。段落应短小精悍，适合移动端阅读，使用恰当的过渡句保证行文的流畅与丝滑。
2. **文学性与表现力 (Literary Expression)**：
   - 拒绝干瘪冰冷的机器生成感（AI 味）。多运用生动的**隐喻和类比 (Analogies)** 来降低复杂技术的理解门槛，使枯燥的代码和架构富有生命力。
   - 词汇选择应精准且富有张力，用词具备专业度与力量感（例如：用“重塑”代替“改变”，用“破局”代替“解决”）。
   - 注重行文的节奏感，长短句结合，娓娓道来。
3. **共情与人称 (Empathy & Tone)**：行文必须采用**第一人称复数**（“我们”、“大家”），拉近与读者的距离，营造“我们在共同探讨与成长”的社区氛围。**严禁使用**带有居高临下说教感或疏离感的“你”、“你的”。
4. **生成标题**：采用新媒体爆款标题逻辑，突出价值感、悬念或痛点共鸣（例如：“Agent江湖的大一统前夜”、“为什么我们还在写面条代码？”），拒绝平铺直叙的流水账标题。
5. **生成摘要**：高度凝练文章核心价值，**必须严格控制在 60-120 字以内**，这是各大平台对摘要长度的硬性要求。
6. **确定合集 (Collection)**：合集分类选项仅限 `"AI"` 或 `"Agent"` 这两个选项，不能使用其他任何名称。

### Step 2: 视觉设计与插图生成（多图排版）

**封面（cover）是必填项。为了打破视觉单调，强烈建议在文章正文的关键节点（如架构讲解、痛点对比处）生成并插入多张高质量插图。** 

**优先级 1：使用 AI 图像生成工具（首选）**
如果当前 Agent 环境支持生成图片（例如具备 `generate_image` tool），**必须优先使用 AI 绘图能力**来设计精美的封面和文章配图，并保存到 payload 目录。

**优先级 2：使用 Text-to-Diagram（兜底）**
只有在当前 Agent **不支持**生成图片的情况下，才退而求其次，利用代码能力编写**结构图 (PlantUML) 或流程图 (Mermaid)**，并调用 `generate-diagram` 工具生成图片。

> **注意：** 现代文章应追求视觉丰富度。请为不同的逻辑段落设计不同的视觉表达，避免封面和正文插图重复。正文中的图片请直接使用 Markdown 原生语法（如 `![架构图](architecture.png)`）插入合适的位置。
> **注意：** 如果使用 Mermaid 生成 Sequence Diagram (时序图)，请务必在文件顶部添加 `%%{init: {'sequence': {'mirrorActors': false}}}%%`，以隐藏底部的参与者名称，保持图片清爽。

**调用示例（CLI 模式兜底）**：

```bash
# 1. 编写代码
cat << 'EOF' > payload_dir/cover.mmd
graph TD
    A[Idea] --> B[AI Writer]
    B --> C[Blogger-Agent]
    C --> D[WeChat Official Account]
EOF

# 2. 生成图片
blogger generate-diagram --type mermaid --input payload_dir/cover.mmd --output payload_dir/cover.png
```

如果是在 MCP 模式下兜底，请直接将代码传递给 `generate_diagram` tool，将 `output_path` 指向 payload 目录。

### Step 3: 构造 Payload 目录

1. **确定保存位置**：默认情况下，必须在当前项目目录下的 `articles/` 文件夹中，以**文章标题**为名创建一个专属子目录作为 Payload 目录（例如 `articles/OpenAI的四层分层架构/`）。如果用户在对话中明确指定了保存位置参数，则以用户指定的路径为准。
2. 确保所有生成的封面和插图都已经放置在该专属目录中。
3. **关键步骤**：在该专属目录中创建并写入 Markdown 文件（例如 `artical.md` 或使用文章标题本身命名）。

**Markdown 格式规范（必须严格遵守）**：

此格式由 `publish.py` 内部的状态机进行严格解析，任何不符合 Front Matter 格式的文件都将导致解析失败。

```markdown
---
title: "这里是富有张力的文章标题"
author: "Agent"
desc: "这里是文章简介，高度凝练核心观点，长度必须严格控制在 60 到 120 个字符之间。"
collection: "AI"
cover: "cover.png"
---

这里开始是文章的正文内容。首段应当作为“钩子”，迅速抓住读者的痛点或引发共鸣。

### 核心架构剖析

我们在探讨复杂系统时，往往需要一张清晰的架构图来破局：

![核心架构](architecture.png)

段落之间要注意承上启下。多图混排能极大地提升阅读体验。

![流程说明](workflow.png)

最后，通过掷地有声的总结来升华主题。
```

注意事项：
- 必须在 Markdown 文件头部使用标准的 YAML Front Matter 格式（由 `---` 包围）。
- `title`, `author`, `desc`, `collection`, `cover` 这些字段名必须准确无误。
- `cover` 填写的是相对于 payload 目录的封面文件名，**这是必填项**。
- `illustration` 字段已不再强制要求于 Front Matter 中，**请务必直接在正文中使用 `![alt](filename.png)` 的原生语法进行多图混排**。
- 从第二个 `---` 以下的所有内容，均会被视为公众号文章正文。

### Step 4: 执行发布脚本

内容准备就绪后，使用 bash 运行发布命令（借助 `uvx` 实现零安装执行）：

```bash
uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./articles/你的文章标题目录
```

该脚本将自动接管 Google Chrome（使用 macOS 的 AppleScript 和 ChromeDomController），自动寻找或打开微信公众号后台（`mp.weixin.qq.com`），并将你生成的 Markdown 渲染、注入文本、设置原创、设置合集并上传封面插图。

**监控与异常处理**：
1. 观察脚本运行输出，注意是否有 `WARNING` 级别报错（如“Summary length is XX chars”）。
2. 如果提示 “WeChat Official Account tab not found”，说明当前浏览器中没有打开微信公众号页面。你需要提醒用户在 Chrome 中手动登录一次微信公众号后台。

## Example Usage

**用户输入**：
```
帮我写一篇关于 Agent 自动化的文章，发到微信草稿。
```

**执行流程**：
1. 扩写大纲并生成 60-120 字的简介。
2. 使用 AI 图像生成工具（或 Mermaid 兜底）生成封面和插图，分别保存为 `articles/Agent自动化/cover.png` 和 `articles/Agent自动化/illustration.png`。
3. 创建 `articles/Agent自动化/artical.md`（或者以文章标题命名），填充所需标签。
4. 执行 `uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./articles/Agent自动化`。
5. 等待脚本完成，向用户报告草稿已保存，并提醒其在手机或浏览器预览确认。
