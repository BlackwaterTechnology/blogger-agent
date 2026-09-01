---
name: generate-photo-message
description: Use when the user asks to create, design, or publish a WeChat Photo Message (图片消息 / 小绿书图文 / 微信画册 / 竖版知识卡片), or explicitly invokes `/generate-photo-message` or `/photo-message`. Trigger phrases include "生成图片消息", "制作图片消息", "发小绿书", "做小绿书图文", "微信图片消息", "图文卡片", "切片做成图片消息". It produces a 3:4 vertical high-resolution card deck (1200x1600) and structured markdown copy. Once drafted, it MUST dispatch a subagent to review the assets.
---

# Generate Photo Message Skill (微信图片消息 / 小绿书制作)

## Overview

把任意输入（长文切片、深度观点、技术架构、实战方法论、商业认知）转化为**高点击率（High CTR）、3:4 竖版高密排版、极简短语化、直通公域推荐池**的微信图片消息（小绿书/微信画册） Payload。

微信官方对“图片消息”给予极高的**公域算法推荐权重**（“看一看”、订阅号消息瀑布流卡片推荐、“搜一搜”）。本 Skill 是专门针对此形态打造的**视觉卡片建模 + 爆破文案编排 + 自动化渲染**流水线。

---

## 核心底层哲学：4 大硬核业务假设

1. **【极化爆破钩子假设】(Hook Dissonance)**：
   - 移动端信息流中，首图决定 80% 的点击率。封面**绝对禁止**平铺 20+ 字的技术全长标题。
   - 封面大标题必须提炼为 **4 ~ 8 字认知冲突短语/爆破钩子**（如 `0.99刀的真相？`、`穿仓的必然性`），CTR > 10%。
2. **【3:4 竖版高密画册假设】(Visual Density Floor)**：
   - 统一采用移动端黄金比例 **3:4**（`1200 x 1600 px`）。
   - 单张卡片以 **4 ~ 8 字短语** 与 **高对比度模块卡片** 承载，字号严格保持 **≥ 22px**，将滑动率与完播率拉升至 70%+。
3. **【切片沉淀与公域破圈双轮驱动】(Matrix Synergy)**：
   - 长文做深度沉淀与私域专家壁垒；图片消息做公域推荐破圈与快速涨粉。两者互相链接，形成内容矩阵。
4. **【T-A-O 认知协作架构】(Orchestration)**：
   - 人类负责 Context Framing（高维问题定义与冲突提炼）；AI 负责卡片建模、SVG 矢量绘制与批处理高清渲染。

---

## 📱 移动端优先（Mobile-First）排版与字符底线（CRITICAL）

微信图片消息的描述文案输入框（Description）在微信端具有 **1000 字符硬性上限**。为确保发布 100% 成功且具备移动端阅读沉浸感，必须遵守以下铁律：

1. **伴随文案字符硬顶（Strict 350 ~ 700 字符，上限绝对 ≤ 900 字符）**：
   - 伴随文案是“导读与互动引流”，**严禁把长文内容全盘堆砌进伴随文案**。
   - 纯文本字符数（含 Emoji、空格、标点）严格控制在 **350 ~ 700 字符之间**，**绝对禁止超过 900 字符**，为系统话题与标签预留充足安全空间。
2. **轻量小绿书文案排版（No Markdown Clutter）**：
   - 禁用 `###`、`##` 等原生 Markdown 标记，段落小标题统一使用 `【模块标题】` 或 Emoji 引导（如 `【一、痛点与现实困境】`、`📌 核心支柱`）。
   - 禁用 `---` 分割线。
   - 引用统一使用 `💡 核心洞察：` 引导行，禁用 `>` 语法。
   - 列表项使用原生 Unicode 符号（`• ` 或 `1. `）。
   - 强调使用自然标点（如「」、“”），避免大面积使用 `**粗体**` 产生字符噪点。
3. **字号硬性底线（Font Size Floor）**：
   - **大标题 / Hook 核心词**：`42px ~ 68px`（超粗加重）
   - **模块标题 / Badge 标签**：`26px ~ 34px`
   - **正文要点 / 节点说明**：**严格禁止低于 22px ~ 24px**！在手机端缩放后低于 22px 的文字无法辨识。
4. **极致短语化（Extreme Abstraction）**：
   - 卡片节点文字控制在 **4 ~ 8 个字以内**（短语化、符号化、加粗关键词如 `第一性原理 · 边界审计`）。
   - **严禁在卡片中堆砌整段长句或复杂段落**。
5. **统一原生符号（No LaTeX）**：
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
1. 爆破 Hook（4-8字）：封面想击穿读者哪个固有偏见？（如：0.99刀的真相？/ 穿仓的必然性）
2. 社交货币命名实体：本文提炼了哪 1 个具备传播力的概念/方法论？（如：1.111B Class / 动态 Delta 引擎）
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
- 微信合集 collection：必须且只能从 blogger.toml 的 photo_collections 列表中选择。
- 伴随文案字数：严格控制在 350 ~ 700 字符（上限绝对 ≤ 900 字符），0 Markdown 语法污染。
- 符号规范：100% 使用原生 Unicode 符号，0 LaTeX 行内公式。
```

---

### 阶段 2：3:4 高清认知卡片集生成

1. **创建 Payload 目录**：
   `articles/YYYY-MM-DD-photo-<slug>/`（如 `articles/2026-09-01-photo-domain-pricing-xyz`）。

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
title: "0.99刀的真相？ ｜ 揭秘 6 元域名与行业暴利定价"
author: "Agent"
desc: "60-120字的凝练摘要"
type: "photo" # 声明为图片消息
collection: "DevSecOps图文" # 必须且只能从 blogger.toml 中的 photo_collections 选取
creation_source: "个人观点，仅供参考" # 可选，支持：个人观点，仅供参考 / 内容由AI生成
tags: ["域名注册", "云计算", "避坑指南"]
photos:
  - "01_cover.png"
  - "02_vs_comparison.png"
  - "03_bullet_points.png"
  - "04_pipeline_steps.png"
  - "05_summary_cta.png"
---
```

#### 正文排版结构示范（严格 350 ~ 700 字符，上限 ≤ 900 字符）
```markdown
# 0.99刀的真相？ ｜ 揭秘 6 元域名与行业暴利定价

💡 核心洞察：买域名绝不能只看首年促销价。域名本质是“租借资产”，全生命周期的持有成本完全取决于第二年及以后的续费价格与隐藏条款。

【.xyz 6~9 位纯数字为什么这么便宜？】
「6 位及以上纯数字的 .xyz 域名只要 6~7 元/年」并非短期促销，而是 .xyz 注册局推出的长期战略项目——“1.111B Class”：
• 规则范围：涵盖 6~9 位纯数字，组合多达 11.11 亿个。
• 续费同价：官方批发底价固定，零售约 $0.80 ~ $0.99/年，持有永不涨价。
• 最佳场景：极度适合个人服务器、DDNS 动态解析、API 测试或 Web3 地址绑定。

【低成本注册实操避坑四步法】
1. 全局比价（TLD-List）：购买前务必查清注册、续费和转入三项价格。
2. 认准零加价平台：优先选择 Cloudflare Registrar（成本直售）、Porkbun 等良心平台。
3. 按需配置后缀：测试脚本选 .xyz 纯数字；正式品牌项目优先考虑 .com。
4. 利用 Transfer 降本：低价首年域名在 60 天后转入 Cloudflare 锁定成本。

💬 互动探讨：
你注册过最便宜或最贵的域名是多少钱？在选购和续费中踩过哪些刺客套路？欢迎在评论区分享你的实战经验！

#域名注册 #云计算 #建站技巧 #开发者工具 #微信小绿书 #网络基础设施
```

---

### 阶段 4：Dispatch Review (Subagent)

**CRITICAL INSTRUCTION**: 卡片与文案生成完成后，**严禁直接发布**。
你必须调用子代理（`@self` 或 `@generalist`）并指示其使用 `review-article` 或针对图片消息的打分卡进行审查：
- 伴随文案纯文本字符数是否严格在 **350 ~ 700 字符** 且 **≤ 900 字符**？
- 卡片是否为严格 3:4 比例（1200x1600）？
- 移动端字号是否全部 ≥ 22px？
- 封面是否有 4~8 字爆破 Hook？
- 正文是否为 0 LaTeX 公式、0 Markdown 语法污染（无 `###`、`---`、`**`）？
- `collection` 是否严格属于 `blogger.toml` 的 `photo_collections`？

审查通过后，即可提示用户使用 `/publish-article` 进行推送！

