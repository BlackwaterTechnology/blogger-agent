---
name: generate-article
description: Use when the user asks to write a technical article, blog post, or WeChat draft, or explicitly uses the `/generate-article` slash command. Trigger phrases include "/generate-article", "写一篇文章", "整理成博客", "帮我发个草稿". The skill produces a Markdown payload directory (front matter + 正文 + 配图). Once drafted, it MUST dispatch a subagent to review the article.
---

# Generate Article Skill

## Overview

把任意输入（草稿、对话、观点、技术笔记）转化为**结构清晰、论点锐利、以图代言**的中文技术文章，生成插图与封面。

与浏览器自动化不同，此 skill 走的是「Markdown payload + CLI」管道。本 skill 同时是**创作助手 + 编辑助手 + 建模助手**：它会逼你先想清楚「主张是什么」「证据是什么」「哪些概念该建模成图」再开写。

**核心原则：模型 / 图表 / 数据图 > 文字描述。** 一张架构图、状态机、对比雷达、流程图能解释清楚的事，不要写成 200 字段落让读者自己脑补。技术写作里能图示化的对象（架构、流程、调用链、状态变化、分类层级、数据分布、维度对比）就建模成图——文字只用来补图无法说清的细节、上下文、推理。

## Required Tools

- **bash**：跑图片生成子进程。
- **文件系统**：建 Payload 目录、保存图片与 Markdown。
- **图片生成**（按内容类型分工，参数详见阶段 2）：
  - **角色 / 场景化封面、概念意象图**：原生 AI 绘图工具（如 `generate_image`）。
  - **排版式封面（书评 / 杂志风）**：Python `matplotlib`（无 AI 绘图工具时的兜底）。
  - **结构化图表（架构 / 流程 / 拓扑 / 思维导图 / 对比网格）**：本地离线渲染优先：
    - `~/bin/plantuml.jar`（PlantUML，**首选引擎**。排版精密，可控性强，支持高 DPI。配合 `!pragma layout smetana` 无需 Graphviz）
    - `~/bin/mmdc`（官方 `@mermaid-js/mermaid-cli`，Puppeteer + Dagre 布局，**备选/极简图表引擎**）
  - **最后兜底**：`blogger generate-diagram --type mermaid|plantuml --input x --output x.png`（kroki.io，受公网限制，仅本地工具不可用时使用）
- **封面 letterbox 工具**：`~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py`（随 skill 分发）——把任意比例的封面 letterbox 到目标比例（默认 16:9，可选 1:1），支持 `--bg white|black|auto|#RRGGBB` 与 `-o/--output` alias。详见 §2.3。

## Workflow

执行任务时**必须按顺序**走完以下阶段。

---

### 阶段 1：双重自检（实质 + 形式）

在生成任何 Markdown 或图片之前，**必须在回复中先输出以下两份自检并填答**。两份都答完才能进入阶段 2。

#### A. 内容质量自检（这一步决定文章好不好）

```text
【内容质量自检】
1. 一句话主张：这篇文章想让读者改变看法 / 学到的那一句话是什么？
   - 必须是陈述句、有动词、有立场。
   - 反例："Agent Harness 的演进趋势"（话题，不是主张）
   - 正例："Harness 不再是工程师的护城河，模型本身正在吞掉框架"

2. 反直觉点：这个主张里最让读者意外 / 反共识的点是什么？
   - 如果你答不出来，先回去重新打磨主张，再继续。

3. 证据清单：我准备用哪 2-3 件具体证据支撑主张？必须落到下面至少两类：
   □ 代码 / 命令 / 配置片段
   □ 数据 / 数字 / 时间线
   □ 真实产品、项目、人物的具体例子（带名字）
   □ 引用或一手资料（带出处）
   ⚠ 不允许全文都是「我们认为」「业界普遍」「值得思考」这类无证据陈述。

4. 视觉建模清单：本文有哪 2-4 个对象值得建模成图？至少打勾 2 类，每类写明"画什么 + 用哪种图"：
   □ 架构 / 拓扑 / 组件关系 → Mermaid `flowchart` 或 PlantUML `component`
   □ 时序 / 调用链 / 协议交互 → Mermaid `sequenceDiagram`
   □ 状态机 / 生命周期 → Mermaid `stateDiagram` 或 PlantUML
   □ 决策树 / 流程 / 算法步骤 → Mermaid `flowchart` 或 PlantUML `activity`
   □ 概念分类 / 思维层级 / 大纲 → PlantUML `mindmap` / `@startwbs`
   □ 时间线 / 演进 / 版本史 → Mermaid `timeline` 或 PlantUML
   □ 数据分布 / 占比 / 工作量 → matplotlib 饼图 / 条形 / 堆叠
   □ 维度对比 / 评分 / 雷达 → matplotlib 雷达图 + Markdown 表格
   □ 类比 / 隐喻 / 场景化封面 → AI 绘图 / 自定义 SVG
   □ 真实截图 / 终端输出 / 用户手稿 → 用户素材（§2.0 优先）
   ⚠ "想不到要画什么"通常意味着主张/证据还不具体——回去重新打磨第 1-3 题，别硬凑图。
   ⚠ **大段文字描述一个能画出来的东西**（架构、流程、对比、状态机），是技术写作的最大反模式。优先想"这段能不能换成一张图 + 一句话说明"。

5. 文章类型：这是哪种文章？(选一个，决定阶段 3 的结构)
   □ 现象解读 / 新闻评论：hook → 事实 → 我的解读 → 影响
   □ 技术解析 / 概念科普：钩子 → 类比 → 拆解 → 边界
   □ 产品 / 项目对比：场景 → 维度对比 → 推荐
   □ 经验沉淀 / 踩坑：背景 → 操作 → 翻车 → 教训
   □ 观点檄文 / 立场：论点 → 反方 → 论据 → 重申
   □ 书评 / 读书笔记：钩子 → 这本书在说什么 → 我同意的部分 → 我不同意/补充的部分 → 它适合谁不适合谁
   ⚠ 默认套「痛点→方案→总结」是套路化的根源，不要选这个。
   ⚠ 书评不要硬塞「观点檄文」——书评的力气应该花在"复述 + 校准"，而不是"开战"。
```

#### B. 形式自检

```text
【形式自检】
- 人称：全文使用「我们/大家」，不用「你/你的」（带说教感）。
- 摘要 desc 长度严格 60–120 字符。
- cover 必填且文件名固定为 cover.png。
- 正文配图 ≥ 2 张（来自 1A Q4 视觉建模清单），每张图必须在文中被显式引用并解释，不能孤儿。
- 优先级：模型 / 图表 / 数据图 > AI 生成插图 > 装饰性图。封面除外。
```

---

### 阶段 2：视觉资产生成

依据阶段 1A 的 **Q4 视觉建模清单** + 证据清单 + 文章类型，规划配图。**第一步永远是 §2.0 素材盘点——先看用户给了什么**，再决定要不要新生成。然后 §2.2 表把 Q4 勾的每一项映射到具体工具，挨个产出。

#### 2.0 素材盘点：先看用户给了什么（在生成任何新图之前）
1. **列清单**：把会话里出现过的每张图过一遍，记下"画的是什么"。
2. **逐张定用途**：
   - **当正文配图**：截图、产品图、终端输出——拷贝进 Payload 目录，按语义重命名。
   - **当封面**：构图紧凑、视觉冲击强的图，letterbox 到 16:9 或 1:1。严禁使用横向图当封面。
   - **跳过**：模糊 / 跑题图。
3. **找缺口**：剩下的视觉需求才是新生成的目标。
4. **位置原则**：每张图必须紧跟它支撑的那段正文，严禁文末堆砌。

#### 2.1 数量与命名
- **必出 1 张封面**：`cover.png`。严禁常规横向流程图当封面。
- **正文图 2–4 张起步**。
- 文件名要语义化（如 `harness-vs-runtime.png`）。源码（.mmd, .puml）一并保留。

#### 2.2 工具选择
| 配图类型 | 推荐工具 |
|---|---|
| 角色 / 场景 / 概念封面 | `generate_image` 等 AI 绘图 |
| 流程图 / 架构图 / 状态机 / 时序图 | `plantuml.jar`（**首选，排版精密清晰**）或 `mmdc`（仅用于极简单线流图） |
| 思维导图 / 分类树 / 标题封面 | `plantuml.jar` (`@startmindmap`) |
| 饼图 / 数据可视化 | Python `matplotlib` |
| 雷达图 / 对比表 / 结构化矩阵 | `plantuml.jar`（利用 `-[hidden]right-` 等控制为扁平网格） |

#### 2.3 渲染命令
参考本地渲染工具规范。
- **PlantUML 渲染与超分**：直接运行 `java -jar ~/bin/plantuml.jar -png <input.puml>`。在 `.puml` 源码首部必须加上 `skinparam dpi 300` 以及 `skinparam Shadowing false`，并且为了美观，首行应加上 `hide stereotype`，使用圆角框及马卡龙/扁平风格配色（如 `#e3f2fd` 表示蓝框，`#ffebee` 表示红框），保障 Retina 高画质与现代审美。
- **Mermaid 超分渲染**：使用 `mmdc` 编译 `.mmd` 时，必须显式附加 `-s 3` 或 `--scale 3` 参数进行超分辨率缩放（例如 `mmdc -s 3 -i input.mmd -o output.png`），确保最终的 PNG 图片在高分屏下文字清晰可见。
- **微信封面处理**：所有封面必须最后执行一次 `fit_wechat_cover.py` 转换至目标比例。

#### 2.4 构图与布局守则
- **“宽图优先，情愿宽而不要高”原则**：正文插图宁可宽一些（横向拉开），也绝不接受高而窄的纵向图。高图极其不适合手机和网页阅读。
  - **Mermaid 规范**：首选 `graph LR`；如果内部有子流程，通过 `direction LR` 将子图横向化。
  - **PlantUML 规范**：使用 `left to right direction` 将默认流转为水平；或者对于双层模型（如冰山模型、矩阵对比），使用 `-[hidden]right-`（而非 `-[hidden]down-`）将元素在同一排拉开，让整体构图呈现 **1.5:1 至 2.5:1 之间的黄金扁平比**。
- **文字精简**：图表节点内部的文本必须极度精简（限制在 4-8 个字内，仅作为短语标识），严禁塞入长句，详细逻辑在正文中解释。
- **横纵比窗口**：正文插图 1.2:1 ~ 2.5:1（严禁高度大于宽度的纵向插图）。封面 16:9 或 1:1。
- **节点数控制**：单图节点数限制在 12 个以下。
- **颜色和字号**：合理控制，避免过饱和度刺眼配色，统一风格。


#### 2.5 渲染后必查
用 `Read` 打开PNG：文字无溢出、无重叠、方向正确、比例合理、中文清晰。不达标则重渲。

---

### 阶段 3：起草 Markdown（按文章类型选骨架）

在 Payload 目录下创建 `article.md`。Front matter **格式固定**，正文骨架**按阶段 1 选定的文章类型**走对应模板。

#### Front Matter（固定）
```markdown
---
title: "[有张力、不平铺直叙的标题]"
author: "Agent"
desc: "[60–120 字符摘要，凝练主张与反直觉点]"
collection: "[必填] 严格从项目根目录 blogger.toml -> platforms.wechat.accounts.default.article_collections 中选择一个（精确匹配，区分大小写）"
cover: "cover.png" # 必填且固定
---
```

#### 正文骨架

根据【文章类型】选择合理的行文结构，确保：
- 每张生成的图都有 `![图注：...](xx.png)` 的引用。
- 图不堆砌在文末，必须紧贴解释段落。

---

### 阶段 4：Dispatch Review (Subagent)

**CRITICAL INSTRUCTION**: Writing is now complete, but you MUST NOT proceed to publish.
You MUST dispatch a subagent (`@generalist`) and instruct it to review your drafted `article.md` using the `review-article` skill.

**Action to take:**
1. Call the `invoke_agent` tool.
2. Set `agent_name` to `generalist`.
3. Set `prompt` to: `Please review the article draft at [Path to article.md] using the 'review-article' skill. Ensure you follow all pre-flight checks and apply necessary edits to the file.`

Once the subagent completes its review, inform the user they can now run `/publish-article` to push it to the platform. Do not run the publish command yourself.
