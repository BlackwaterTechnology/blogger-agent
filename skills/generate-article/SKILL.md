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

1. **【极化主张假设】(Click Dissonance)**：标题必须具备反直觉张力与明确立场（CTR > 8%）。拒绝平铺直叙的话题陈述。**严禁在标题中使用 ` ｜ `、` —— `、` - ` 及两侧空格**，前 18~22 字符必须具备独立且完整的认知爆破力，标点统一使用中文冒号 `：`、问号 `？` 或自然标点。
2. **【图文认知密度假设】(Visual Density)**：人脑处理图形比文本快 60,000 倍。用结构图表（PlantUML / SVG）替代冗长文字，将完读率提升至 50%+。
3. **【社交货币假设】(Social Currency)**：微信朋友圈转发的本质是“自我人设塑造”。文章必须提炼至少 **1 个命名实体或方法论框架**（如 T-A-O 架构、审核权倒置悖论），转发率 > 5%。
4. **【T-A-O 人机协同假设】(Orchestration)**：人类负责 Context Framing（问题高维定义）与 Checklist 终审背书；AI 负责 80% 的资料检索与文本草稿编译。

---

## 📱 移动端优先（Mobile-First）排版与字号规范

针对微信手机端（375px~414px 屏宽，正文有效宽度约 340px~380px，基准缩放比约为 360px），所有生成的正文渲染图片必须严格遵守**移动端优先排版与字号底线**，彻底根除“小字密密麻麻在手机端无法看清”的痛点：

### 1. 缩放比与推荐画布尺寸 (Canvas Viewport Standard)
- **推荐标准画布宽度：`1200px`**（缩放比为 $360 / 1200 = 0.30$，显著优于 1600px 画布的 0.225，文字在手机端具有极佳的视觉张力）。
- **常用画布宽高比**：
  - **双栏对比 / 2x2 矩阵 / 分层架构**：`viewBox="0 0 1200 800"` (3:2) 或 `viewBox="0 0 1200 900"` (4:3)
  - **垂直 3~4 步流转拓扑**：`viewBox="0 0 1200 1000"` 或 `viewBox="0 0 1200 1200"`（纵向长图）
  - **文章封面 (cover.svg)**：`viewBox="0 0 1920 1080"` 或 `viewBox="0 0 1200 675"` (16:9)

### 2. 五级字号阶梯与硬性底线 (Font Size Hierarchy on 1200px Canvas)
| 视觉层级 | 1200px 画布字号 | 手机端映射视觉大小 | 适用场景 |
|---|---|---|---|
| **L1 画布大标题** | `44px ~ 52px` | 13.2px ~ 15.6px (超粗) | 全图核心主标题 |
| **L2 分类徽标 / 阶段 Pill** | `28px ~ 32px` | 8.4px ~ 9.6px (加粗) | 顶部分类 Badge、步骤序号 Pill |
| **L3 卡片标题 / 关键指标** | `36px ~ 42px` | 10.8px ~ 12.6px (加粗) | 模块卡片标题、大号百分比/数据对比 |
| **L4 正文核心短语 / 节点** | `32px ~ 36px` | 9.6px ~ 10.8px (中粗) | 核心概念、关键动作、结论要点 |
| **L5 辅助说明 / 底部注记** | `28px ~ 30px` | 8.4px ~ 9.0px (常规) | 辅助短语、避坑说明、底部 Takeaway |
| **⛔ 绝对硬性底线** | **`≥ 28px`** | — | **全图绝对禁止任何低于 28px 的文字**！（若使用 1600px 画布，底线必须提升至 `≥ 36px`） |

### 3. 防拥挤布局三大铁律 (Anti-Clutter Layout Rules)
1. **【横向最多 2 栏 (Max 2 Horizontal Columns)】**：
   - **严禁在单张图内横向并排 3 栏或 4 栏卡片**！
   - 多步骤流程（3~4 步）**必须采用垂直纵向流转（Top-to-Bottom Stacked Pipeline）**或 **2x2 四象限网格**。
   - 方案/策略对比必须采用**垂直纵向堆叠卡片**或**标准双栏对抗 (2-Column VS)**。
2. **【极致短语化与行数硬顶 (Max 2-3 Lines per Card)】**：
   - 每个卡片/节点内部**严格限制在 2 ~ 3 行文字以内**。
   - 每行文字控制在 **8 ~ 14 个字**（短语化、符号化连接如 `签名验签 · 0 Gas 代付`）。
   - **严禁在图片中填入多行整句长句或解释段落**。详细推导与背景全盘留给 Markdown 正文。
3. **【视觉与文本职责清晰分工】**：
   - 移动端插图 = **高对比度视觉锚点与结构模型 (Visual Anchor & Mental Model)**
   - 正文 Markdown = **严密推理逻辑与长句表达 (Narrative)**

---

## Required Tools

- **bash**：跑图片生成子进程。
- **文件系统**：建 Payload 目录、保存图片与 Markdown。
- **图片生成**（按内容类型分工，参数详见阶段 2）：
  - **瑞士平面排版封面（首选/无AI噪点）**：`python tools/generate_cover.py` (支持 `swiss_red`, `navy_gold`, `emerald`, `slate_lime` 4 种杂志级主题配色)。
  - **扁平矢量概念封面**：`generate_image` 等 AI 绘图工具（**必须带 2D 扁平矢量 Prompt 约束，严禁 3D 霓虹/发光脑/科幻 HUD/假文字等 AI 俗套**）。
  - **二维坐标轴 / 精美自定义图表**：AI 生成或手写原生 SVG，利用 macOS 系统的 `sips` 工具进行本地 PNG 渲染。在需要高主观审美颜值、非标准或精确的坐标轴与信息图卡片时使用。
  - **结构化图表（架构 / 流程 / 拓扑 / 思维导图 / 对比网格）**：本地离线渲染优先：
    - `~/bin/plantuml.jar`（PlantUML，**基础流程/思维导图备选**。排版精密，可控性强，支持高 DPI。配合 `!pragma layout smetana` 无需 Graphviz）
    - `~/bin/mmdc`（官方 `@mermaid-js/mermaid-cli`，Puppeteer + Dagre 布局，**备选/极简图表引擎**）
  - **最后兜底**：`blogger generate-diagram --type mermaid|plantuml --input x --output x.png`（kroki.io，受公网限制，仅本地工具不可用时使用）
- **封面 letterbox 工具**：`tools/fit_wechat_cover.py`——把任意比例的封面 letterbox 到目标比例（默认 16:9，可选 1:1），支持 `--bg white|black|auto|#RRGGBB` 与 `-o/--output` alias。详见 §2.3。

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

4. 视觉建模清单：本文有哪 2-4 个对象值得建模成图？至少打勾 2 类（提倡具象隐喻与结构拓扑组合），每类写明"画什么 + 用哪种模态"：
   □ 【模态 1】具象概念隐喻 / 场景对抗 → AI 绘图 `generate_image`（5大去俗套艺术风格，如蒸汽机械vs极简机器人、古代石壁代码）
   □ 【模态 2】架构 / 拓扑 / 分层关系 → 原生 SVG 分层架构（字号≥28px，支持白底/暗蓝/暖灰）
   □ 【模态 2】时序 / 调用链 / 协议交互 → 原生 SVG 垂直流水线（字号≥28px，严禁横向4列）
   □ 【模态 2】状态机 / 决策树 / 生命周期 → 原生 SVG 纵向流动或 PlantUML `activity` (DPI 300+)
   □ 【模态 2】概念分类 / 思维层级 / 大纲 → PlantUML `mindmap` / `@startwbs` (字号≥24px)
   □ 【模态 3】维度选型 / 4 象限策略矩阵 → 原生 SVG 2x2 网格（字号≥28px）
   □ 【模态 3】二元对抗 / 方案对比矩阵 → 原生 SVG 双栏对抗矩阵（字号≥28px）
   □ 【模态 4】收益走势 / 基差剪刀差 / 分布 → matplotlib 统计曲线 (DPI 300+) 或 原生 SVG 走势
   □ 【模态 4】真实终端输出 / 代码 Diff / 手稿 → 用户素材 / CLI 终端卡片
   ⚠ "想不到要画什么"通常意味着主张/证据还不具体——回去重新打磨第 1-3 题，别硬凑图。
   ⚠ 拒绝全篇单一深蓝 SVG：提倡在开篇或核心矛盾处引入【模态 1】具象概念隐喻图，激活读者右脑。

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
- 标题排版：前 18~22 字符必须包含完整认知钩子，0 ` ｜ ` / ` —— ` / 空格污染，标点统一使用全角中文标点。
- 人称：全文使用「我们/大家」，严格不用「你/你的」（带说教感）。
- 摘要 desc 长度严格 60–120 字符。
- 微信合集 collection：必须且只能从配置文件 blogger.toml 的 [platforms.wechat.accounts.default].article_collections 列表中选择（如 AI, Agent, AWS, Web3, DevSecOps, 认知思维, 信息安全, Iac, 云原生）。
- cover 必填且文件名固定为 cover.png。
- 正文配图 ≥ 2 张（来自 1A Q4 视觉建模清单），每张图必须在文中被显式引用并解释，不能孤儿。
- 配图模态与色彩多样性：
  - 是否避免了全篇 100% 冰冷单一深蓝图？是否合理混配了具象概念隐喻图（模态1）或非单一暗黑主题？
  - 若包含 AI 绘图，是否严格杜绝了发光蓝脑、机械手、科幻 HUD、乱码假字等 AI 俗套？
  - 1200px 画布下 SVG 图表所有文字是否严格 ≥ 28px（核心节点 ≥ 32px）？
  - 是否严格遵守横向最多 2 栏（多步骤一律垂直纵向流转）？
  - 单卡片文字是否控制在 2-3 行极简短语内？无长句堆砌？
```

---

### 阶段 2：视觉资产生成

#### 2.0 素材盘点：先看用户给了什么
1. 列出会话中已有的素材图。
2. 决定用途（正文插图、封面或忽略）。

#### 2.1 数量与命名
- **必出 1 张封面**：`cover.png`（16:9 或 1:1）。
- **正文图 2–4 张起步**，语义化命名（如 `caveman-metaphor.png`, `tao-architecture.png`, `policy-quadrant.png`）。

#### 2.2 4 大视觉模态矩阵与黄金混配 SOP (Multi-Modal Visual Strategy)

为打破“全篇全盘深蓝 SVG 蓝图”的视觉疲劳，文章必须根据内容性质，从以下 4 大视觉模态中进行组合：

| 模态标识 | 配图类型 | 推荐工具 | 核心价值与适用场景 | 关键约束与风格 |
|---|---|---|---|---|
| **🎨 模态 1** | **具象概念隐喻 / 场景插画** | `generate_image` (AI 绘图) | 开篇破局、现象隐喻、反直觉对比、角色冲突、生活化类比。激活右脑情感与好奇心。 | **5 大去 AI 味艺术风格**（见 §2.6），严禁蓝光脑/机械手/乱码字，强调具体物理实体与场景故事。 |
| **📐 模态 2** | **结构拓扑 / 垂直时序流** | 原生 SVG / PlantUML | 核心机制拆解、端到端时序流、3 层架构拓扑。提供精密的工程心智模型。 | 1200px 画布，字号 ≥28px-36px，**多主题色板**（暗蓝/极简白/暖陶土/森林绿），垂直纵向流动。 |
| **📊 模态 3** | **多维决策矩阵 / 二元对抗** | 原生 SVG (2x2 网格 / 双栏对抗) | 新旧对比、4 象限技术选型、8 大策略分类。提供结构化决策清单。 | 2 栏对抗或 2x2 四象限网格，高对比度 Badge，卡片内 2-3 行极简短语。 |
| **📈 模态 4** | **实证量化图表 / 终端切片** | Matplotlib / 原生 SVG / 终端 Mockup | 收益率走势、基差价差剪刀差、实测 Benchmark、CLI 终端输出。提供无可辩驳的硬核证据。 | DPI 300+，专业金融终端/科研期刊排版质感。 |

##### 黄金混配比例（The Golden Mix SOP）
对于一篇包含 3~4 张图的深度长文，**推荐采用“感性隐喻 ➔ 严密拓扑 ➔ 决策落地”的节奏编排**：
- **封面 (Cover)**：双栏复合杂志封面（模式 1）或 概念场景插图叠加 Hook（模式 3）。
- **配图 1（引入/矛盾/破局）**：**【模态 1】具象概念隐喻图**（如用蒸汽机械 vs 折纸天鹅比喻框架笨重与模型轻量，或山顶洞人石壁代码）。
- **配图 2（核心机制/流转拆解）**：**【模态 2】原生大字号 SVG 架构/时序拓扑**（垂直流水线或 3 层架构，提供严谨工程认知）。
- **配图 3（选型/对比/实证）**：**【模态 3 或 4】2x2 四象限矩阵 / 双栏对抗 / Matplotlib 收益曲线**（给出终局落地依据）。

##### 2.2.1 原生 SVG 优先与防小字防截断铁律（CRITICAL）
- 结构类插图优先使用**原生 SVG 矢量图编写**，画布推荐使用 `viewBox="0 0 1200 H"`。
- **严禁在 1600px 画布中使用低于 36px 的文字，严禁在 1200px 画布中使用低于 28px 的文字**。
- 若使用 PlantUML 渲染后出现字号偏小、文字裁切或质感发灰，**必须立即重写为原生 SVG 模板并重新渲染**。

#### 2.3 渲染命令（1080p~2K 标准与 DPI 300+ 规范）
- **SVG / PNG 高画质渲染 (sips)**：设计 `.svg` 源码使用推荐的 `viewBox="0 0 1200 H"`（封面 `1920 1080`）。转换命令**必须包含 `--resampleWidth 1920`**：
  `sips -s format png --resampleWidth 1920 <input.svg> --out <output.png>`
- **PlantUML 高清渲染**：`java -jar ~/bin/plantuml.jar -png <input.puml>`。源码头部加入 `skinparam dpi 300`、`skinparam Shadowing false`、`skinparam pageWidth 2400`。

#### 2.4 封面设计高阶规范 (Editorial Cover Design Standards)

**严禁把正文全长标题直接填入封面**！封面是社交吸引力锚点，必须遵守**【双栏复合杂志架构 (Composite Editorial Layout)】**：

1. **解耦“封面 Hook”与“正文 H1 标题”**：
   - **封面大标题**：必须炼字为 **4 ~ 8 字认知冲突爆破短语**（例如：“11% 的谎言？”、“穿仓的必然性”），字号保持 `64px ~ 76px`，绝不使用 20+ 字的全长技术标题。
   - **正文标题**：保留完整的 SEO 严密技术标题。

2. **双栏复合杂志排版 (Dual-Column Architecture)**：
   - **左栏 (40% 宽度)**：分类 Badge + 极简爆破短语 + 副标题 + 品牌/日期 Header。
   - **右栏 (60% 宽度)**：**必须包含高对比度微型信息图/数据对比卡片 (Micro-Infographic Card)**（卡片内字号保持 `28px ~ 34px`）。

3. **三种封面模式分级**：
   - **模式 1 (强制首选)：复合矢量信息图封面** (默认必须使用 SVG 设计左文 Hook + 右侧微型信息图卡片，`sips -s format png --resampleWidth 1920` 渲染)，严禁生成无右侧信息图卡片的平铺标题封面。
   - **模式 2：大字极简数据冲突封面** (突出巨大核心数据对比 `11% ➔ 3%`)。
   - **模式 3：AI 概念场景插图 + 文字叠加** (`generate_image` 生成无字 2D 矢量图 + 叠加爆破 Hook)。

---

#### 2.5 移动端原生 SVG 标杆设计范式 (4 High-Readability SVG Archetypes)

在编写正文 SVG 插图时，**必须直接参考或套用以下 4 套大字号、高对比度、防拥挤的现代杂志级 SVG 范式**：

##### 范式 A：双栏高对比对抗矩阵 (2-Column VS Comparison)
适用于：传统模式 vs 现代模式、旧痛点 vs 新架构、中心化 vs 去中心化对比。
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 820" width="1200" height="820">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#1E293B" />
    </linearGradient>
  </defs>
  <rect width="1200" height="820" fill="url(#bg)" />

  <!-- Header Section -->
  <g transform="translate(60, 50)">
    <rect x="0" y="0" width="180" height="36" rx="18" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5" />
    <text x="90" y="24" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="20" font-weight="700" text-anchor="middle">架构演进对比</text>
    <text x="0" y="80" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="46" font-weight="900">传统模式 vs 现代签名代付</text>
  </g>

  <!-- 2-Column Container -->
  <g transform="translate(60, 180)">
    <!-- Left Column: Legacy (525px width) -->
    <g transform="translate(0, 0)">
      <rect width="525" height="440" rx="16" fill="#141B2D" stroke="#EF4444" stroke-width="2" />
      <rect width="525" height="60" rx="16" fill="#450A0A" />
      <rect y="40" width="525" height="20" fill="#450A0A" />
      <text x="30" y="42" fill="#FCA5A5" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">❌ 传统模式：两阶段交互</text>

      <g transform="translate(30, 95)">
        <text x="0" y="25" fill="#F87171" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">步骤 1：链上 Approve</text>
        <text x="0" y="70" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 必须持有 ETH 扣除 Gas</text>
        
        <line x1="0" y1="110" x2="465" y2="110" stroke="#334155" stroke-width="1.5" />

        <text x="0" y="155" fill="#F87171" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">步骤 2：TransferFrom 划转</text>
        <text x="0" y="200" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 二次 Gas 消耗 + 串行等待</text>

        <rect y="240" width="465" height="70" rx="10" fill="#2A1215" stroke="#7F1D1D" stroke-width="1" />
        <text x="20" y="284" fill="#FCA5A5" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">⚠️ 痛点：无 ETH 时遭遇入金死锁</text>
      </g>
    </g>

    <!-- Right Column: Modern Paradigm (525px width) -->
    <g transform="translate(555, 0)">
      <rect width="525" height="440" rx="16" fill="#141B2D" stroke="#10B981" stroke-width="2" />
      <rect width="525" height="60" rx="16" fill="#064E3B" />
      <rect y="40" width="525" height="20" fill="#064E3B" />
      <text x="30" y="42" fill="#6EE7B7" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">✅ 现代范式：Permit 签名代付</text>

      <g transform="translate(30, 95)">
        <text x="0" y="25" fill="#34D399" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">步骤 1：链下离线签名</text>
        <text x="0" y="70" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 0 Gas 费用，私钥瞬时签名</text>
        
        <line x1="0" y1="110" x2="465" y2="110" stroke="#334155" stroke-width="1.5" />

        <text x="0" y="155" fill="#34D399" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">步骤 2：Relayer 原子代付</text>
        <text x="0" y="200" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 官方节点全额代付并划转</text>

        <rect y="240" width="465" height="70" rx="10" fill="#062E24" stroke="#047857" stroke-width="1" />
        <text x="20" y="284" fill="#6EE7B7" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">💡 优势：零门槛入金，单笔原子确认</text>
      </g>
    </g>
  </g>

  <!-- Bottom Takeaway Banner -->
  <g transform="translate(60, 650)">
    <rect width="1080" height="110" rx="14" fill="#0B1329" stroke="#38BDF8" stroke-width="1.5" />
    <text x="35" y="46" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">💡 核心认知跃迁</text>
    <text x="35" y="86" fill="#E2E8F0" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">将 Gas 支付与交易发起权解耦，把多阶段链上摩擦转化为单次原子签名。</text>
  </g>
</svg>
```

##### 范式 B：垂直流水线时序拓扑 (Vertical Linear Pipeline)
适用于：多步骤时序交互、端到端数据流转、发布/执行流水线。**严禁横向 4 列挤压，必须采用垂直堆叠**。
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 980" width="1200" height="980">
  <defs>
    <linearGradient id="bg_pipeline" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0A0F1D" />
      <stop offset="100%" stop-color="#141C2E" />
    </linearGradient>
  </defs>
  <rect width="1200" height="980" fill="url(#bg_pipeline)" />

  <!-- Header -->
  <g transform="translate(60, 50)">
    <rect x="0" y="0" width="200" height="36" rx="18" fill="#1E293B" stroke="#10B981" stroke-width="1.5" />
    <text x="100" y="24" fill="#10B981" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="20" font-weight="700" text-anchor="middle">端到端执行链路</text>
    <text x="0" y="80" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="46" font-weight="900">零 ETH 存款：签名与中继时序拓扑</text>
  </g>

  <!-- 3-4 Vertical Pipeline Cards (1080px width each) -->
  <g transform="translate(60, 175)">
    <!-- Step 1 Card -->
    <g transform="translate(0, 0)">
      <rect width="1080" height="150" rx="14" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5" />
      <rect x="25" y="25" width="120" height="38" rx="8" fill="#0284C7" />
      <text x="85" y="51" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="800" text-anchor="middle">STEP 01</text>
      <text x="165" y="52" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">用户前端发起离线签名</text>
      <text x="165" y="105" fill="#94A3B8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">触发 EIP-712 签名请求 · <tspan fill="#38BDF8" font-weight="700">0 Gas 纯私钥签名</tspan> · 产出 (v, r, s)</text>
    </g>

    <!-- Arrow 1 -->
    <text x="540" y="195" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="36" font-weight="bold" text-anchor="middle">⬇</text>

    <!-- Step 2 Card -->
    <g transform="translate(0, 220)">
      <rect width="1080" height="150" rx="14" fill="#1E293B" stroke="#818CF8" stroke-width="1.5" />
      <rect x="25" y="25" width="120" height="38" rx="8" fill="#4F46E5" />
      <text x="85" y="51" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="800" text-anchor="middle">STEP 02</text>
      <text x="165" y="52" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">官方 Relayer 聚合代付</text>
      <text x="165" y="105" fill="#94A3B8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">中继节点作为 msg.sender · <tspan fill="#818CF8" font-weight="700">官方全额代付 Gas</tspan> · 批量打包上链</text>
    </g>

    <!-- Arrow 2 -->
    <text x="540" y="415" fill="#818CF8" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="36" font-weight="bold" text-anchor="middle">⬇</text>

    <!-- Step 3 Card -->
    <g transform="translate(0, 440)">
      <rect width="1080" height="150" rx="14" fill="#1E293B" stroke="#10B981" stroke-width="1.5" />
      <rect x="25" y="25" width="120" height="38" rx="8" fill="#059669" />
      <text x="85" y="51" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="800" text-anchor="middle">STEP 03</text>
      <text x="165" y="52" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">智能合约密码学校验与原子入账</text>
      <text x="165" y="105" fill="#94A3B8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">合约执行 ecrecover 验证签名 · <tspan fill="#34D399" font-weight="700">原子划转资金</tspan> · 状态瞬时同步</text>
    </g>

    <!-- Bottom Takeaway -->
    <g transform="translate(0, 630)">
      <rect width="1080" height="110" rx="14" fill="#022C22" stroke="#10B981" stroke-width="1.5" />
      <text x="35" y="46" fill="#34D399" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">⚡ 架构核心收益</text>
      <text x="35" y="86" fill="#D1FAE5" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">实现真正意义上的「Web2 级流畅体验」与「Web3 级私钥自托管安全」。</text>
    </g>
  </g>
</svg>
```

##### 范式 C：2x2 四象限分类网格 (2x2 Quadrant Matrix)
适用于：策略分类、风险矩阵、技术选型四象限评估。
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 860" width="1200" height="860">
  <defs>
    <linearGradient id="bg_quad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B0E14" />
      <stop offset="100%" stop-color="#141923" />
    </linearGradient>
  </defs>
  <rect width="1200" height="860" fill="url(#bg_quad)" />

  <g transform="translate(60, 45)">
    <text x="0" y="40" fill="#F59E0B" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="46" font-weight="900">Redis 淘汰策略四象限决策矩阵</text>
    <text x="0" y="80" fill="#94A3B8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">根据数据特征与业务风险选择最优内存淘汰算法</text>
  </g>

  <!-- 2x2 Grid Container -->
  <g transform="translate(60, 160)">
    <!-- Top-Left Card -->
    <g transform="translate(0, 0)">
      <rect width="525" height="290" rx="14" fill="#141B2D" stroke="#6366F1" stroke-width="2" />
      <text x="25" y="48" fill="#818CF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">allkeys-lru (纯缓存首选 ⭐⭐⭐)</text>
      <text x="25" y="105" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 规则：淘汰全量键中最久未访问</text>
      <text x="25" y="150" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 场景：符合二八定律的读多业务</text>
      <rect x="25" y="200" width="475" height="55" rx="8" fill="#1E2648" />
      <text x="40" y="238" fill="#A5B4FC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">推荐：Web 页面 / 实体数据缓存</text>
    </g>

    <!-- Top-Right Card -->
    <g transform="translate(555, 0)">
      <rect width="525" height="290" rx="14" fill="#141B2D" stroke="#38BDF8" stroke-width="2" />
      <text x="25" y="48" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">allkeys-lfu (防扫描穿透 ⭐⭐⭐)</text>
      <text x="25" y="105" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 规则：淘汰全量键中访问频次最低</text>
      <text x="25" y="150" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 场景：防止批处理 Scan 污染热点</text>
      <rect x="25" y="200" width="475" height="55" rx="8" fill="#0C4A6E" />
      <text x="40" y="238" fill="#7DD3FC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">推荐：高并发电商 Feed / 计数器</text>
    </g>

    <!-- Bottom-Left Card -->
    <g transform="translate(0, 320)">
      <rect width="525" height="290" rx="14" fill="#1C1814" stroke="#F59E0B" stroke-width="2" />
      <text x="25" y="48" fill="#FBBF24" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">volatile-ttl (生命周期驱动 ⭐⭐)</text>
      <text x="25" y="105" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 规则：仅在带 TTL 键中挑最短者淘汰</text>
      <text x="25" y="150" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 场景：显式依 TTL 分级的临时状态</text>
      <rect x="25" y="200" width="475" height="55" rx="8" fill="#451A03" />
      <text x="40" y="238" fill="#FDE68A" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">推荐：验证码 / 动态风控临时标记</text>
    </g>

    <!-- Bottom-Right Card -->
    <g transform="translate(555, 320)">
      <rect width="525" height="290" rx="14" fill="#1C1417" stroke="#EF4444" stroke-width="2" />
      <text x="25" y="48" fill="#F87171" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">noeviction (拒写保真 / 默认)</text>
      <text x="25" y="105" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 规则：内存满后写操作直接报错 OOM</text>
      <text x="25" y="150" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 场景：强一致业务，绝对禁止丢数据</text>
      <rect x="25" y="200" width="475" height="55" rx="8" fill="#3D1219" />
      <text x="40" y="238" fill="#FCA5A5" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">注意：必须配合外部容量告警与扩容</text>
    </g>
  </g>
</svg>
```

##### 范式 D：3 层分层系统架构拓扑 (3-Tier Layered Architecture)
适用于：系统分层、协议栈、技术架构拆解。
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 880" width="1200" height="880">
  <defs>
    <linearGradient id="bg_arch" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="100%" stop-color="#1E293B" />
    </linearGradient>
  </defs>
  <rect width="1200" height="880" fill="url(#bg_arch)" />

  <g transform="translate(60, 45)">
    <rect x="0" y="0" width="160" height="36" rx="18" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5" />
    <text x="80" y="24" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="20" font-weight="700" text-anchor="middle">系统架构拓扑</text>
    <text x="0" y="80" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="46" font-weight="900">T-A-O 认知协作分层架构</text>
  </g>

  <!-- 3 Horizontal Stacked Layers (1080px width each) -->
  <g transform="translate(60, 165)">
    <!-- Layer 1: Context Layer -->
    <g transform="translate(0, 0)">
      <rect width="1080" height="175" rx="14" fill="#141B2D" stroke="#38BDF8" stroke-width="2" />
      <rect x="25" y="25" width="160" height="38" rx="8" fill="#0284C7" />
      <text x="105" y="51" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="800" text-anchor="middle">LAYER 01 · 顶层</text>
      <text x="210" y="52" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">Context Framing（问题高维定义）</text>
      <text x="25" y="110" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 人类专家主导 · 提炼极化主张与反直觉命题 · 设定业务边界</text>
      <text x="25" y="148" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">核心产出：第一性原理假设、命名实体与关键论据清单</text>
    </g>

    <!-- Arrow 1 -->
    <text x="540" y="208" fill="#38BDF8" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="32" font-weight="bold" text-anchor="middle">⬇</text>

    <!-- Layer 2: Automation Layer -->
    <g transform="translate(0, 235)">
      <rect width="1080" height="175" rx="14" fill="#141B2D" stroke="#818CF8" stroke-width="2" />
      <rect x="25" y="25" width="160" height="38" rx="8" fill="#4F46E5" />
      <text x="105" y="51" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="800" text-anchor="middle">LAYER 02 · 核心</text>
      <text x="210" y="52" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">AI Agent 编译与矢量建模引擎</text>
      <text x="25" y="110" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 自动化资料聚合 · 原生大字号 SVG 渲染 · 爆破文案生成</text>
      <text x="25" y="148" fill="#818CF8" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">核心产出：图文 Payload、2K 渲染卡片与 Markdown 实体</text>
    </g>

    <!-- Arrow 2 -->
    <text x="540" y="443" fill="#818CF8" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="32" font-weight="bold" text-anchor="middle">⬇</text>

    <!-- Layer 3: Verification Layer -->
    <g transform="translate(0, 470)">
      <rect width="1080" height="175" rx="14" fill="#141B2D" stroke="#10B981" stroke-width="2" />
      <rect x="25" y="25" width="160" height="38" rx="8" fill="#059669" />
      <text x="105" y="51" fill="#FFFFFF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="22" font-weight="800" text-anchor="middle">LAYER 03 · 终审</text>
      <text x="210" y="52" fill="#F8FAFC" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="800">Checklist 机器终审与发布管道</text>
      <text x="25" y="110" fill="#CBD5E1" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 移动端字号机检 (≥28px) · 消除 AI 腔 · 一键发布至多平台</text>
    </g>
  </g>
</svg>
```

---

#### 2.6 去除“AI味”的 5 大艺术风格 Prompt 范式 (5 High-Taste Editorial AI Styles)

使用 `generate_image` 生成具象概念隐喻图（模态 1）时，**必须坚决杜绝 4 大廉价 AI 俗套**：
- ❌ **严禁蓝光/紫色发光大脑 (Glowing Brains)**
- ❌ **严禁机器人与人类手指相触/机械手握手 (Cybernetic Hands Shaking)**
- ❌ **严禁科幻全息 HUD 悬浮面板与满屏代码雨 (Hologram Matrix HUD)**
- ❌ **严禁画面中出现 AI 生成的无意义扭曲乱码英文字符 (Garbled Pseudo-Text)**

必须直接采用国际顶级杂志（*The New Yorker*, *The Economist*, *Wired*, *Monocle*）的 **5 大高审美艺术流派**：

##### 风格 1：现代杂志社论扁平插画 (Modern Editorial Flat Vector)
- **适用场景**：商业逻辑、组织分工、认知偏差、产品理念。
- **Prompt 模板**：
  `Modern editorial vector illustration, flat 2D graphic design, elegant bold silhouettes, clean textured geometry, contemporary magazine style, subtle paper texture, cohesive sophisticated color palette of slate gray, warm amber, and deep navy, high contrast, award-winning editorial art. Scene depicting [具体场景/具象动作，如 an architect assembling modular puzzle blocks while discarding bloated blueprints]. No text, no words, no 3D glossy render.`

##### 风格 2：实体机械/物理隐喻对比 (Physical Mechanical Metaphor)
- **适用场景**：重型框架 vs 轻量内核、传统低效 vs 现代极速、山顶洞人极简 Token 压缩。
- **Prompt 模板**：
  `Conceptual physical metaphor illustration, vintage intricate mechanism contrasting with sleek modern minimalist artifact, rich tactile textures, warm atmospheric cinematic lighting, clear visual contrast, editorial storytelling art. Scene showing [具体物理对比，如 an enormous heavy steampunk cast-iron engine overflowing with gears and smoke pipes compared side by side with an ultra-lightweight geometric origami crane floating effortlessly]. High visual density, crisp detail, no text, no glowing sci-fi clichés.`

##### 风格 3：复古清晰线稿与版画 (Vintage Ligne Claire / Moebius & Woodcut)
- **适用场景**：认知哲学、博弈论、系统脆弱性、历史反思。
- **Prompt 模板**：
  `Ligne claire illustration style, Moebius inspired ink line art with subtle watercolor wash, delicate hatched shading, intellectual graphic novel aesthetic, matte muted earth tones (terracotta, olive green, cream paper). Scene showing [具体画面，如 an ancient scholar and a futuristic automaton playing a game of chess on an intricate labyrinth board]. High aesthetic, literary tone, clean composition, zero text.`

##### 风格 4：等轴测微缩黏土模型 (Isometric Clay & Papercraft Diorama)
- **适用场景**：数据孤岛、跨链套利流水线、分布式集群、安全防火墙。
- **Prompt 模板**：
  `Isometric stylized miniature diorama, handcrafted matte clay and folded paper aesthetic, soft tactile studio lighting, pastel and architectural color harmony of mint green, soft slate, and cream, clean focal composition. Scene showing [微缩系统场景，如 a miniature financial fortress with tiny vaults connected by clean optical pipelines, protected from storm clouds]. Studio photography feel, tactile materials, no garbled text, no neon glows.`

##### 风格 5：包豪斯构成主义与瑞士印画 (Bauhaus Constructivism & Swiss Screenprint)
- **适用场景**：第一性原理、架构解耦、去中心化平衡、极致极简主义。
- **Prompt 模板**：
  `Bauhaus constructivist graphic art, Swiss international typographic style, bold abstract geometric forms, diagonal dynamic balance, matte screen print texture, primary red, deep navy, and raw cream paper background. Concept representing [抽象物理力学平衡，如 a minimalist fulcrum balancing a giant boulder with a single delicate feather]. High tension, graphic poster art, no random AI noise.`

---

#### 2.7 SVG 多主题色板系统与明色/暖色范式 (Multi-Theme Palette System)

原生 SVG 插图不再局限于单一深蓝底色！必须根据文章领域与情绪基调自由选用以下 **4 款杂志级主题色板**：

| 色板名称 | 背景色 (Canvas) | 卡片底色 (Card) | 主强调色 (Primary) | 辅助色 (Accent) | 适用领域 |
|---|---|---|---|---|---|
| **`slate_navy`** (深曜黑蓝) | `#0F172A` | `#141B2D` / `#1E293B` | `#F59E0B` (琥珀金) | `#38BDF8` (青蓝) / `#10B981` (翠绿) | 硬核系统、AI 底层、金融量化 |
| **`swiss_white`** (瑞士白底) | `#F8F9FA` | `#FFFFFF` | `#E63946` (瑞士红) | `#1D3557` (深海蓝) / `#059669` (祖母绿) | 商业评论、认知哲学、极简社论 |
| **`terracotta_warm`** (暖陶米纸) | `#FAF5EF` | `#FFFFFF` / `#F5EBE1` | `#EA580C` (陶土橙) | `#65A30D` (橄榄绿) / `#78350F` (深褐) | 职场方法、认知成长、教育人生 |
| **`forest_emerald`** (深林薄荷) | `#022C22` | `#064E3B` | `#10B981` (薄荷绿) | `#34D399` (嫩绿) / `#F0FDF4` (象牙白) | 工程效能、开源治理、增长模型 |

##### 范式 E：明色/白底瑞士社论对抗矩阵 (Swiss White 2-Column VS)
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 820" width="1200" height="820">
  <!-- Clean Off-White Background -->
  <rect width="1200" height="820" fill="#F8F9FA" />

  <!-- Header Section -->
  <g transform="translate(60, 50)">
    <rect x="0" y="0" width="180" height="36" rx="18" fill="#E5E7EB" />
    <text x="90" y="24" fill="#374151" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="20" font-weight="700" text-anchor="middle">认知思维模型</text>
    <text x="0" y="80" fill="#111827" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="46" font-weight="900">廉价信号 vs 硬核背书模型</text>
  </g>

  <!-- 2-Column Container -->
  <g transform="translate(60, 180)">
    <!-- Left Column: Cheap Signaling (525px) -->
    <g transform="translate(0, 0)">
      <rect width="525" height="440" rx="16" fill="#FFFFFF" stroke="#EF4444" stroke-width="2" />
      <rect width="525" height="60" rx="16" fill="#FEE2E2" />
      <rect y="40" width="525" height="20" fill="#FEE2E2" />
      <text x="30" y="42" fill="#B91C1C" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">❌ 廉价信号：低成本表态</text>

      <g transform="translate(30, 95)">
        <text x="0" y="25" fill="#DC2626" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">口头承诺 · 无抵押品</text>
        <text x="0" y="70" fill="#4B5563" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 伪造边际成本接近 0</text>
        
        <line x1="0" y1="110" x2="465" y2="110" stroke="#E5E7EB" stroke-width="1.5" />

        <text x="0" y="155" fill="#DC2626" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">短期投机 · 零违约惩罚</text>
        <text x="0" y="200" fill="#4B5563" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 败露后无实际资产损失</text>

        <rect y="240" width="465" height="70" rx="10" fill="#FEF2F2" stroke="#FCA5A5" stroke-width="1" />
        <text x="20" y="284" fill="#991B1B" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">⚠️ 结果：沦为博弈论中的柠檬劣币</text>
      </g>
    </g>

    <!-- Right Column: Hard Proof (525px) -->
    <g transform="translate(555, 0)">
      <rect width="525" height="440" rx="16" fill="#FFFFFF" stroke="#059669" stroke-width="2" />
      <rect width="525" height="60" rx="16" fill="#D1FAE5" />
      <rect y="40" width="525" height="20" fill="#D1FAE5" />
      <text x="30" y="42" fill="#065F46" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">✅ 硬核信号：非对称代价</text>

      <g transform="translate(30, 95)">
        <text x="0" y="25" fill="#059669" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">真实沉淀 · 锁定质押</text>
        <text x="0" y="70" fill="#4B5563" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 需要支付不可逆的时间或资本</text>
        
        <line x1="0" y1="110" x2="465" y2="110" stroke="#E5E7EB" stroke-width="1.5" />

        <text x="0" y="155" fill="#059669" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="34" font-weight="700">长期博弈 · 声誉连带责任</text>
        <text x="0" y="200" fill="#4B5563" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">• 建立不可伪造的极高信任壁垒</text>

        <rect y="240" width="465" height="70" rx="10" fill="#ECFDF5" stroke="#6EE7B7" stroke-width="1" />
        <text x="20" y="284" fill="#065F46" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28" font-weight="700">💡 结果：沉淀为长期垄断社交资产</text>
      </g>
    </g>
  </g>

  <!-- Bottom Takeaway Banner -->
  <g transform="translate(60, 650)">
    <rect width="1080" height="110" rx="14" fill="#FFFFFF" stroke="#D1D5DB" stroke-width="1.5" />
    <text x="35" y="46" fill="#1E40AF" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="30" font-weight="800">💡 第一性原理洞察</text>
    <text x="35" y="86" fill="#374151" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="28">只有承受了不可逆沉没成本的信号，才能穿透噪音建立真实共识。</text>
  </g>
</svg>
```

---

### 阶段 3：起草 Markdown

在 `articles/YYYY-MM-DD-<slug>` Payload 目录下创建 `article.md`。

目录命名强制规范：
- 格式：`articles/YYYY-MM-DD-<slug>`（例如 `articles/2026-08-03-true-nobility`）
- 必须前置当前日期（YYYY-MM-DD），使用连字符 `-` 连接日期与语义化英文 slug。
- **列表空行硬性规范**：无序列表（`*`, `-`）与有序列表（`1.`, `2.`）与其上方的正文段落之间，必须显式插入空行（如 `段落说明：\n\n* 列表项1`），防止在 Blogger / 微信 / CSDN 编辑器中被合并为无换行的单行长段落。

#### Front Matter 规范 (CRITICAL)

`article.md` 头部必须包含合规的 YAML Front Matter：

```yaml
---
title: "文章标题"
author: "Agent"
desc: "60-120字的凝练摘要"
collection: "AI" # ⚠️ 微信文章合集：必须且只能从 blogger.toml 的 article_collections 列表中选择！
cover: "cover.png"
---
```

**`collection` (微信文章合集) 强制校验规则**：
- `collection` 字段值**必须且只能**选择自项目根目录 `blogger.toml` 中 `[platforms.wechat.accounts.default].article_collections` 定义的有效合集名称列表（例如 `["AI", "Agent", "AWS", "Web3", "DevSecOps", "认知思维", "信息安全", "Iac", "云原生"]`）。
- 严禁在 Front Matter 中填入未在 `blogger.toml` 中配置的合集名称。若需要新增合集，必须先编辑 `blogger.toml` 添加对应项目后再使用。

---

### 阶段 4：Dispatch Review (Subagent)

**CRITICAL INSTRUCTION**: Writing is now complete, but you MUST NOT proceed to publish.
You MUST dispatch a subagent (`@self` 或 `@generalist`) 并指示其使用 `review-article` skill 审阅草案。

完成审阅后，告知用户可运行 `/publish-article` 进行推送。
