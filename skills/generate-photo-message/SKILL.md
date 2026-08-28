---
name: generate-photo-message
description: Use when the user asks to create, design, or publish a WeChat Photo Message (图片消息 / 小绿书图文 / 微信画册 / 竖版知识卡片), or explicitly invokes `/generate-photo-message` or `/photo-message`. Trigger phrases include "生成图片消息", "制作图片消息", "发小绿书", "做小绿书图文", "微信图片消息", "图文卡片", "切片做成图片消息". It produces a 3:4 vertical high-resolution card deck (1200x1600) and structured markdown copy. Once drafted, it MUST dispatch a subagent to review the assets.
---

# Generate Photo Message Skill (微信图片消息 / 小绿书制作)

## Overview

把任意输入（长文切片、深度观点、技术架构、实战方法论、商业认知）转化为**高点击率（High CTR）、3:4 竖版高密排版、极简短语化、直通公域推荐池**的微信图片消息（小绿书/微信画册） Payload。

微信官方目前正在对“图片消息”给予极高的**公域算法推荐权重**（“看一看”、订阅号消息瀑布流卡片推荐、“搜一搜”）。本 Skill 是专门针对此形态打造的**视觉卡片建模 + 爆破文案编排 + 自动化渲染**流水线。

---

## 核心底层哲学：4 大硬核业务假设

1. **【极化爆破钩子假设】(Hook Dissonance)**：
   - 移动端信息流中，首图决定 80% 的点击率。封面**绝对禁止**平铺 20+ 字的技术全长标题。
   - 封面大标题必须提炼为 **4 ~ 8 字认知冲突短语/爆破钩子**（如 `11% 的谎言？`、`穿仓的必然性`），CTR > 10%。
2. **【3:4 竖版高密画册假设】(Visual Density Floor)**：
   - 统一采用移动端黄金比例 **3:4**（`1200 x 1600 px`）。
   - 人脑处理视觉信息比纯文本快 60,000 倍。单张卡片以 **4 ~ 8 字短语** 与 **高对比度模块卡片** 承载，将完播率与滑动率拉升至 70%+。
3. **【切片沉淀与公域破圈双轮驱动】(Matrix Synergy)**：
   - 长文做深度沉淀与私域专家壁垒；图片消息做公域推荐破圈与快速涨粉。两者互相链接，形成内容矩阵。
4. **【T-A-O 认知协作架构】(Orchestration)**：
   - 人类负责 Context Framing（高维问题定义与冲突提炼）；AI 负责卡片建模、SVG 矢量绘制与批处理高清渲染。

---

## 📱 移动端优先（Mobile-First）排版与字号底线

在 3:4（`1200 x 1600 px`）画布中，所有渲染卡片必须严格遵守以下排版底线：

1. **字号硬性底线（Font Size Floor）**：
   - **大标题 / Hook 核心词**：`42px ~ 68px`（超粗加重）
   - **模块标题 / Badge 标签**：`26px ~ 34px`
   - **正文要点 / 节点说明**：**严格禁止低于 22px ~ 24px**！在手机端缩放后低于 22px 的文字无法辨识。
2. **极致短语化（Extreme Abstraction）**：
   - 卡片节点文字控制在 **4 ~ 8 个字以内**（短语化、符号化、加粗关键词如 `第一性原理 · 边界审计`）。
   - **严禁在卡片中堆砌整段长句或复杂段落**。详细推导与长句全盘交由伴随 Markdown 正文承载。
3. **统一原生符号（No LaTeX）**：
   - 严禁在图表或文案中使用 LaTeX 公式（如 `$\rightarrow$`），必须直接使用原生 Unicode 符号（`→`, `⇒`, `❌`, `✅`, `⚡`, `💬`, `⭐`）。

---

## 🛠️ Required Tools

- **卡片渲染引擎**：`tools/generate_photo_cards.py`（支持单张或通过 JSON/YAML 配置批量生成）。
- **底座模块**：`src/blogger/core/photo_card_generator.py`（内置 5 大布局模板与 4 款杂志级主题配色）。
- **转换工具**：macOS 原生 `sips`（配合 `--resampleWidth 1200` 实现 Retina 级别清晰度，零锯齿与发虚）。
- **文件系统**：管理 `articles/YYYY-MM-DD-photo-<slug>/` 目录结构。

---

## 5 大经典卡片模板矩阵

| 模板标识 | 适用场景 | 关键视觉要素 |
|---|---|---|
| **`cover`** | 首图 Hook / 封面 | 分类 Badge + 4~8 字爆破短语 + 副标题 + 3 行微型数据/认知对比卡 + 滑动提示 |
| **`vs_comparison`** | 二元对抗 / 新旧对比 | 双栏对比矩阵（左侧 ❌ 传统旧模式 vs 右侧 ✅ 现代新范式） + 底部核心结论条 |
| **`bullet_points`** | 核心支柱 / 模块清单 | 3~4 个独立圆角卡片，含序号 Pill、加粗要点、短语描述与底部标签组 |
| **`pipeline_steps`** | 步骤流转 / 工程链路 | 垂直连线流转卡片（Step 01 → Step 02 → Step 03） + 阶段交付物 + 底部铁律栏 |
| **`summary_cta`** | 复盘清单 / 互动引流 | 3~4 项核心 Checklist + 突出的大号互动探讨卡片（💬 提问） + 点赞/收藏/转发栏 |

---

## 🎨 4 套杂志级主题配色 (Cohesive Themes)

- **`navy_gold`**（黑曜曜石蓝 `#0F172A` + 琥珀金 `#F59E0B`）：**首选**。硬核技术、AI 架构、金融量化、系统工程。
- **`swiss_red`**（极简白底 `#F8F9FA` + 瑞士红 `#E63946`）：经典社论、犀利观点、反直觉认知、认知破局。
- **`emerald`**（深邃森林绿 `#022C22` + 薄荷绿 `#10B981`）：工程效能、增长飞轮、开源生态、敏捷治理。
- **`slate_lime`**（暗黑哑光灰 `#18181B` + 荧光青柠 `#84CC16`）：开发者工具、系统底层、黑客极客、基础设施。

---

## Standard Workflow (SOP)

执行任务时**必须按顺序**走完以下 4 个阶段。

---

### 阶段 1：双重自检（实质 + 形式）

在生成任何图片或 Markdown 之前，**必须在回复中输出以下两份自检并填答**：

#### A. 内容质量自检
```text
【图片消息内容质量自检】
1. 爆破 Hook（4-8字）：封面想击穿读者哪个固有偏见？（如：11% 的谎言？/ 穿仓的必然性）
2. 社交货币命名实体：本文提炼了哪 1 个具备传播力的概念/方法论？（如：动态 Delta 引擎 / 三层自愈网）
3. 3~7 张卡片规划清单：
   - 卡片 01 (cover)：爆破 Hook + 核心冲突数据
   - 卡片 02 (vs_comparison / points)：旧模式痛点 vs 新范式解法
   - 卡片 03 (bullet_points / pipeline)：三大支柱 / 关键机制
   - 卡片 04 (pipeline_steps / points)：四步实操落地链路
   - 卡片 05 (summary_cta)：Checklist 闭环 + 1 个评论区争议互动问题
```

#### B. 形式自检
```text
【形式自检】
- 画布比例：严格 3:4 竖版（1200 x 1600 px）。
- 字号底线：标题 ≥ 42px，正文节点 ≥ 22px，无整段长句堆砌。
- 配色主题：统一从 navy_gold / swiss_red / emerald / slate_lime 中选取 1 种。
- 微信合集 collection：必须且只能从 blogger.toml 的 article_collections 列表中选择。
- 符号规范：100% 使用原生 Unicode 符号，0 LaTeX 行内公式。
- 伴随文字：300~800 字，列表上方显式插入空行。
```

---

### 阶段 2：3:4 高清认知卡片集生成

1. **创建 Payload 目录**：
   `articles/YYYY-MM-DD-photo-<slug>/`（如 `articles/2026-08-28-photo-delta-neutral`）。

2. **编写卡片配置或脚本**：
   在 Payload 目录下创建 `deck_spec.json`（或 `generate_deck.py`），使用 `tools/generate_photo_cards.py` 批处理生成高清卡片：

```bash
# 批量渲染整套卡片
python tools/generate_photo_cards.py --config articles/YYYY-MM-DD-photo-<slug>/deck_spec.json --output-dir articles/YYYY-MM-DD-photo-<slug>/
```

3. **产物检查**：
   确保生成的图片命名规范：
   - `01_cover.png`
   - `02_vs_comparison.png`
   - `03_bullet_points.png`
   - `04_pipeline_steps.png`
   - `05_summary_cta.png`

---

### 阶段 3：起草精炼伴随文案 (`article.md`)

在 Payload 目录下编写 `article.md`。

#### Front Matter 规范 (CRITICAL)
```yaml
---
title: "爆破 Hook：4-8字核心主张 ｜ 完整副标题"
author: "Agent"
desc: "60-120字的凝练摘要"
type: "photo" # 声明为图片消息
collection: "AI" # 必须且只能从 blogger.toml 中的 article_collections 选取
tags: ["AI", "架构设计", "动态编排"]
photos:
  - "01_cover.png"
  - "02_vs_comparison.png"
  - "03_bullet_points.png"
  - "04_pipeline_steps.png"
  - "05_summary_cta.png"
---
```

#### 正文排版结构（300 ~ 800 字）
```markdown
# 爆破 Hook：4-8字核心主张 ｜ 完整副标题

> 💡 **核心洞察**：一句话直击痛点，指出传统做法的盲区与新范式的必然性。

---

### 痛点与现实困境

在复杂现实场景中，静态经验往往成为最大的脆弱点：

* **单点直觉依赖**：缺乏可复现的度量基准，异常发生时无法追溯。
* **规则硬编码**：面对动态环境变化，边际维护成本呈指数级上升。
* **缺乏韧性自愈**：遇到极端扰动直接崩溃，造成不可逆的系统性穿仓。

---

### 破局：新范式的三大核心支柱

要实现反脆弱的确定性交付，必须在架构层面完成认知重构：

1. **高维问题定义**：在执行前冻结上下文与范围，将不确定性收敛至沙盒。
2. **动态智能编排**：以状态机为基础，实现异常自动感知与降级回滚。
3. **机器终审背书**：建立形式化 Checklist 防线，彻底杜绝主观偏见。

---

### 行动清单与互动讨论

* ☑ 核心资产长文做深度沉淀，知识卡片做公域破圈。
* ☑ 保持 3:4 竖版高密排版，字号严格保持 ≥ 22px。
* ☑ 每张卡片聚焦 1 个核心论点，短语化表达。

---

💬 **互动探讨**：
在你的团队实践中，遇到过哪些因“静态规则”而导致的系统性失效？你是如何破局的？欢迎在评论区分享你的实战经验！

#技术架构 #智能体 #系统设计 #微信小绿书
```

---

### 阶段 4：Dispatch Review (Subagent)

**CRITICAL INSTRUCTION**: 卡片与文案生成完成后，**严禁直接发布**。
你必须调用子代理（`@self` 或 `@generalist`）并指示其使用 `review-article` 或针对图片消息的打分卡进行审查：
- 卡片是否为严格 3:4 比例？
- 移动端字号是否全部 ≥ 22px？
- 封面是否有 4~8 字爆破 Hook？
- 正文是否有 0 LaTeX 公式且列表上方有空行？
- `collection` 是否符合 `blogger.toml`？

审查通过后，即可提示用户使用 `/publish-article` 进行推送！
