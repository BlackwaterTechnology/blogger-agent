---
name: generate-article
description: Use when the user asks to write a technical article, blog post, or WeChat draft, or explicitly uses the `/generate-article` slash command. Trigger phrases include "/generate-article", "写一篇文章", "整理成博客", "帮我发个草稿". The skill produces a Markdown payload directory (front matter + 正文 + 配图). Once drafted, it MUST dispatch a subagent to review the article.
---

# Generate Article Skill

## Overview

把任意输入（草稿、对话、观点、技术笔记）转化为**结构清晰、论点锐利、以图代言、具备高维社交货币**的中文技术与商业文章，生成高清插图与封面。

本 skill 同时是**创作助手 + 编辑助手 + 建模助手**：基于第一性原理（First Principles Thinking）与 **T-A-O 认知协作架构**，逼迫创作过程完成从低维“知识记忆”到高维“架构定义与终审”的跃迁。

---

## 核心底层哲学：4 大硬核业务假设

每一篇文章的创作与视觉建模，均必须建立在以下 4 个可被数据验证的业务假设之上：

1. **【极化主张假设】(Click Dissonance)**：标题必须具备反直觉张力与明确立场（CTR > 8%）。拒绝平铺直叙的话题陈述。
2. **【图文认知密度假设】(Visual Density)**：人脑处理图形比文本快 60,000 倍。用结构图表（PlantUML / SVG）替代冗长文字，将完读率提升至 50%+。
3. **【社交货币假设】(Social Currency)**：微信朋友圈转发的本质是“自我人设塑造”。文章必须提炼至少 **1 个命名实体或方法论框架**（如 T-A-O 架构、审核权倒置悖论），转发率 > 5%。
4. **【T-A-O 人机协同假设】(Orchestration)**：人类负责 Context Framing（问题高维定义）与 Checklist 终审背书；AI 负责 80% 的资料检索与文本草稿编译。

---

## 📱 移动端优先（Mobile-First）排版与字号规范

针对微信手机端（375px~414px 屏宽），所有生成的渲染图片必须严格遵守**移动端优先规范**，防止“小字密密麻麻在手机端无法看清”：

1. **字号硬性底线（Font Size Floor）**：
   - 主标题：`32px ~ 40px`
   - 分类卡片 / 标签：`24px ~ 28px`
   - 正文节点 / 核心关键词：**绝对禁止低于 20px - 22px**！在 1600px 宽度画布中低于 20px 的文字在手机端缩放后会沦为不辨认的微雕。
2. **极致极简短语化（Extreme Abstraction）**：
   - 节点与卡片文本控制在 **4 ~ 8 个字以内**（短语化、短文本列举、符号连接如 `杏仁核主导 · 去甲肾上腺素`）。
   - **严禁在图片中填入多行整句长句或解释段落**。详细逻辑与推导全盘留给 Markdown 正文。
3. **视觉职责分工**：
   - 移动端图片 = **视觉锚点与关键词矩阵 (Visual Anchors)**
   - 正文 Markdown = **推理逻辑与长句表达 (Narrative)**

---

## Required Tools

- **bash**：跑图片生成子进程。
- **文件系统**：建 Payload 目录、保存图片与 Markdown。
- **图片生成**（按内容类型分工，参数详见阶段 2）：
  - **角色 / 场景化封面、概念意象图**：原生 AI 绘图工具（如 `generate_image`）。
  - **排版式封面（书评 / 杂志风）**：Python `matplotlib`（无 AI 绘图工具时的兜底）。
  - **二维坐标轴 / 精美自定义图表**：AI 生成或手写原生 SVG，利用 macOS 系统的 `sips` 工具进行本地 PNG 渲染。在需要高主观审美颜值、非标准或精确的坐标轴与信息图卡片时使用。
  - **结构化图表（架构 / 流程 / 拓扑 / 思维导图 / 对比网格）**：本地离线渲染优先：
    - `~/bin/plantuml.jar`（PlantUML，**首选引擎**。排版精密，可控性强，支持高 DPI。配合 `!pragma layout smetana` 无需 Graphviz）
    - `~/bin/mmdc`（官方 `@mermaid-js/mermaid-cli`，Puppeteer + Dagre 布局，**备选/极简图表引擎**）
  - **最后兜底**：`blogger generate-diagram --type mermaid|plantuml --input x --output x.png`（kroki.io，受公网限制，仅本地工具不可用时使用）
- **封面 letterbox 工具**：`~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py`（随 skill 分发）——把任意比例的封面 letterbox 到目标比例（默认 16:9，可选 1:1），支持 `--bg white|black|auto|#RRGGBB` 与 `-o/--output` alias。详见 §2.3。

---

## Workflow

执行任务时**必须按顺序**走完以下阶段。

---

### 阶段 1：双重自检（实质 + 形式）

在生成任何 Markdown 或图片之前，**必须在回复中先输出以下两份自检并填答**。两份都答完才能进入阶段 2。

#### A. 内容质量自检（这一步决定文章好不好）

```text
【内容质量自检】
1. 一句话主张：这篇文章想让读者改变看法 / 学到的那一句话是什么？
   - 必须是陈述句、有动词、有立场、具备反直觉张力。
   - 反例："Agent Harness 的演进趋势"（话题，不是主张）
   - 正例："Harness 不再是工程师的护城河，模型本身正在吞掉框架"

2. 社交货币与命名实体：本文提炼出了哪 1 个具备传播力的概念实体/方法论？
   - 正例：T-A-O 认知协作架构、审核权倒置悖论、Context Framing。
   - 如果答不上来，重新提炼命名实体后再继续。

3. 证据清单：我准备用哪 2-3 件具体证据支撑主张？必须落到下面至少两类：
   □ 代码 / 命令 / 配置片段
   □ 数据 / 数字 / 时间线
   □ 真实产品、项目、人物、法律判例（带名字）
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
   □ 维度对比 / 评分 / 雷达 → SVG 极简卡片矩阵（字号≥22px）
   □ 类比 / 隐喻 / 场景化封面 → AI 绘图 / 自定义 SVG
   □ 真实截图 / 终端输出 / 用户手稿 → 用户素材（§2.0 优先）
   ⚠ "想不到要画什么"通常意味着主张/证据还不具体——回去重新打磨第 1-3 题，别硬凑图。
   ⚠ 大段文字描述一个能画出来的东西（架构、流程、对比、状态机），是技术写作的最大反模式。

5. 文章类型：这是哪种文章？(选一个，决定阶段 3 的结构)
   □ 现象解读 / 新闻评论：hook → 事实 → 我的解读 → 影响
   □ 技术解析 / 概念科普：钩子 → 类比 → 拆解 → 边界
   □ 产品 / 项目对比：场景 → 维度对比 → 推荐
   □ 经验沉淀 / 踩坑方法论：背景 → 理论/架构 → 实践步骤 → 训练法
   □ 观点檄文 / 立场：论点 → 反方 → 论据 → 重申
   □ 书评 / 读书笔记：钩子 → 这本书在说什么 → 我同意的部分 → 我补充的部分
```

#### B. 形式自检

```text
【形式自检】
- 人称：全文使用「我们/大家」，严格不用「你/你的」（带说教感）。
- 摘要 desc 长度严格 60–120 字符。
- cover 必填且文件名固定为 cover.png。
- 正文配图 ≥ 2 张（来自 1A Q4 视觉建模清单），每张图必须在文中被显式引用并解释，不能孤儿。
- 图表字号：正文图片节点字号是否 ≥ 20px-22px？无长句堆砌？
```

---

### 阶段 2：视觉资产生成

#### 2.0 素材盘点：先看用户给了什么
1. 列出会话中已有的素材图。
2. 决定用途（正文插图、封面或忽略）。

#### 2.1 数量与命名
- **必出 1 张封面**：`cover.png`（16:9 或 1:1）。
- **正文图 2–4 张起步**，语义化命名（如 `tao-architecture.png`）。

#### 2.2 工具选择与移动端极简原则
| 配图类型 | 推荐工具 | 移动端字号要求 |
|---|---|---|
| 角色 / 场景 / 概念封面 | `generate_image` 等 AI 绘图 | N/A |
| 流程图 / 架构图 / 状态机 | `plantuml.jar`（首选） | 节点字号 ≥ 20px |
| 对比矩阵 / 2D 坐标卡片 | **原生 SVG + sips** | 正文字号 ≥ 22px，极简 4-8 字 |
| 思维导图 / 分类树 | `plantuml.jar` (`@startmindmap`) | 节点字号 ≥ 20px |

##### 2.2.1 PlantUML 截断与小字逃逸路径（CRITICAL）
- 若 PlantUML 渲染后图像出现**小字密麻**、**文字裁切**或**图宽估计超过 1600px**，**必须立即切换为原生 SVG 横向泳道布局**（`viewBox="0 0 1600 900"`），正文使用 `22px ~ 24px` 字号，通过 CSS 卡片与 4-8 字短语彻底规避移动端看不清的问题。

#### 2.3 渲染命令（1080p~2K 标准与 DPI 300+ 规范）
- **PlantUML 高清渲染**：`java -jar ~/bin/plantuml.jar -png <input.puml>`。源码头部加入 `skinparam dpi 300`、`skinparam Shadowing false`、`skinparam pageWidth 2400`。
- **SVG / PNG 1080p~2K 渲染 (sips)**：设计 `.svg` 源码使用 `viewBox="0 0 1600 900"`。转换命令**必须包含 `--resampleWidth 1920`**：
  `sips -s format png --resampleWidth 1920 <input.svg> --out <output.png>`

---

### 阶段 3：起草 Markdown

在 `articles/YYYY-MM-DD-<slug>` Payload 目录下创建 `article.md`。

目录命名强制规范：
- 格式：`articles/YYYY-MM-DD-<slug>`（例如 `articles/2026-08-03-true-nobility`）
- 必须前置当前日期（YYYY-MM-DD），使用连字符 `-` 连接日期与语义化英文 slug。

---

### 阶段 4：Dispatch Review (Subagent)

**CRITICAL INSTRUCTION**: Writing is now complete, but you MUST NOT proceed to publish.
You MUST dispatch a subagent (`@self` 或 `@generalist`) 并指示其使用 `review-article` skill 审阅草案。

完成审阅后，告知用户可运行 `/publish-article` 进行推送。
