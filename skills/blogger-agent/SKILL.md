---
name: blogger-agent
description: 多平台文章自动化发布 skill。当用户需要写文章、分享经验、或发布内容到博客平台（微信公众号、掘金、CSDN等）时触发。此 skill 会强制执行结构化内容模板和思考检查单（CoT），以保证人称视角准确并强制配图，随后生成特定格式的 Markdown 并利用 Python CLI 工具自动将文章草稿发布到目标平台。
---

# Blogger Agent

## Overview

将任意输入内容（文章草稿、对话、观点、代码笔记等）转化为结构完整的技术文章，自动生成插图和封面，并调用本地工具自动推送到各大主流博客平台（目前已支持微信公众号，后续将扩展掘金、CSDN 等）。

与纯界面的浏览器自动化不同，此 skill 使用的是封装好的 `blogger` CLI 工具。为了解决生成内容不规范（如遗漏配图、人称错误、格式错误等问题），**Agent 必须严格遵循本规范中的“强制执行流程（CoT 与模板填空）”**。所有发布至微信公众号的文章，系统会自动将创作声明（Creation Source）设置为“个人观点，仅供参考”。

## Required Tools/Servers

执行此 skill 需要以下能力：

- **bash**: 用于运行 Python 发布脚本和子进程图片生成。
- **文件系统**: 用于创建 Payload 目录、保存生成的图片和 Markdown。
- **图片生成能力**：
  - **首选 (AI绘图)**：如果 Agent 具备如 `generate_image` 的工具，优先直接生成图片。
  - **兜底 (代码转图)**：如果不支持绘图，必须编写 Mermaid 或 PlantUML，并通过 `blogger generate-diagram` CLI 命令将代码渲染为图片保存到 Payload 目录。

## Workflow

执行文章发布任务时，**Agent 必须严格按照以下 4 个阶段的顺序逐步执行，绝不可跳过阶段 1**。

### 阶段 1: 强制输出思考检查单 (Chain of Thought)

在开始生成实际 Markdown 文件或生成图片之前，Agent **必须先在回复中输出以下检查单并自我回答**：

```text
【文章规范自我检查】
1. 人称约束：我是否承诺全文只使用“我们/大家”拉近距离，绝不使用带有说教感和距离感的“你/你的”？ (回答：是/否)
2. 封面确认：文章是否需要封面（必填）？封面文件名是否固定为 cover.png？ (回答：是)
3. 插图规划：除了封面，我计划在正文中插入几张说明图？图 1 用来解释什么概念？图 2 (如有)用来解释什么流程？
4. 摘要约束：我设计的摘要是否严格控制在 60 到 120 字之间？
```

只有当你在当前对话中输出了上述检查并确认无误后，才能进入下一阶段。

### 阶段 2: 视觉设计与图片生成

根据阶段 1 的插图规划，使用你的工具生成图片并保存到专属 Payload 目录（如 `articles/文章标题/`）：
- **必须生成至少 1 张封面图** (`cover.png`)。
- **强烈建议生成 1~2 张正文配图**（如 `illustration_1.png`，`illustration_2.png`），用于打破视觉单调。

*(注：如果使用 CLI 模式兜底，请通过 `blogger generate-diagram --type mermaid --input payload_dir/xxx.mmd --output payload_dir/xxx.png` 进行生成)*

### 阶段 3: 严格套用 Markdown 骨架模板

在 Payload 目录中创建 Markdown 文件（可命名为 `article.md` 或 `[文章标题].md`）。
写入内容时，**必须严格复制并填充以下骨架模板**，绝不允许遗漏 Front Matter 或插图的占位符位置：

```markdown
---
title: "这里是富有张力的文章标题（拒绝平铺直叙）"
author: "Agent"
desc: "这里是文章简介，高度凝练核心观点，长度必须严格控制在 60 到 120 个字符之间。"
collection: "AI"  # 仅限填写 "AI" 或 "Agent"
cover: "cover.png" # 必须且固定为此文件名
---

[钩子引题区：使用“我们”，通过生动的隐喻或痛点现象，迅速吸引读者往下看。]

### 1. 核心痛点与背景

[在这里用短小精悍的段落阐述背景，拉近读者距离。]

![[图注：在这里用 Markdown 原生语法插入第一张概念说明图/架构图]](illustration_1.png)

### 2. 破局方案与技术深度

[在这里讲解核心技术逻辑或解决方案。拒绝干瘪的机器生成感，多用类比使枯燥的技术富有生命力。]

![[图注：在这里用 Markdown 原生语法插入第二张技术细节图/流程图]](illustration_2.png)

### 3. 总结与反思

[用掷地有声的总结来升华主题，结束全文。]
```

*(注意：请将 `[...]` 的占位符部分替换为您生成的实际文本，并将 `![...]` 替换为您在阶段 2 实际生成的图片文件名。)*

### 阶段 4: 执行发布脚本

文本和图片准备就绪后，使用 bash 运行发布命令（借助 `uvx` 实现零安装执行）：

```bash
uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./articles/你的文章标题目录
```

**监控与异常处理**：
1. 观察脚本运行输出，留意是否有 `WARNING` 级别报错（尤其是关于 Summary 长度的报错）。
2. 如果提示 “WeChat Official Account tab not found”，说明当前浏览器中没有打开微信公众号页面。你需要提醒用户在 Chrome 中手动登录一次微信公众号后台。

## Example Usage

**用户输入**：
```text
帮我写一篇关于 Agent 自动化的文章，发到微信草稿。
```

**执行流程**：
1. Agent 首先输出【文章规范自我检查】清单，确认人称和配图规划。
2. 确定 Payload 目录为 `articles/Agent自动化/`。使用 AI 绘图工具生成 `cover.png` 和 `illustration_1.png` 并保存至该目录。
3. 严格套用阶段 3 的 Markdown 模板，创建 `articles/Agent自动化/article.md`，并在正文中写入 `![自动化流程](illustration_1.png)`。
4. 执行 `uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./articles/Agent自动化`。
5. 等待脚本完成，向用户报告草稿已保存，并提醒其在手机或浏览器预览。
