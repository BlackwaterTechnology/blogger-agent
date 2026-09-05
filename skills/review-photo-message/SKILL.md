---
name: review-photo-message
description: Use when invoked by a main agent to review a WeChat Photo Message (小绿书/微信图片消息) draft, or explicitly triggered by `/review-photo-message`. It reads the generated `article.md` and `deck_spec.json`, verifies 3:4 vertical cards, checks font sizes, eliminates AI cliches, enforces character count limits, evaluates against the 100-point Photo Rubric, and edits files directly.
---

# Review Photo Message Skill (微信图片消息 / 小绿书专属审核)

## Overview

本 skill 担任微信图片消息（小绿书/微信画册）的**视觉与文案终审官 (Chief Photo Message Evaluator)**。基于 3:4 竖版高密画册理论与公域算法推荐机制，它对目标 Payload 目录下的 `article.md`、`deck_spec.json` 以及渲染产出的 3:4 高清卡片进行专属百分制品控审查，彻底拦截文字溢出、小字截断、文案超长（微信 1000 字符硬顶）与 Markdown 标记污染，并直接修正文件。

---

## 质量审核四大维度（专属百分制打分卡）

审核者必须按照以下 100 分制标准评估并修正图片消息草案与卡片：

```
                      ┌──────────────────────────────────────────────┐
                      │    微信图片消息专属质量打分卡 (Photo Rubric - 100分) │
                      └──────────────────────┬───────────────────────┘
                                             │
        ┌──────────────────┬─────────────────┴────────────────┬──────────────────┐
        ▼                  ▼                                  ▼                  ▼
 【1. 视觉卡片与排版】35分 【2. 爆破封面与认知Hook】25分     【3. 伴随文案与质感】20分  【4. 互动传播与合规】20分
 · 3:4比例与1200px宽度(10)· 4-8字爆破冲突Hook (10)         · 350-700字硬约束(7)     · 标题≤20字与0破折号(6)
 · 字号≥28px底线无溢出(10)· 3行高对比度微型认知卡 (8)       · 换行独立与0粘连(7)     · desc摘要≤120字硬顶(5)
 · 模板流转与键名合规 (8)· 0 AI俗套(蓝脑/机械手/乱码)(7)    · 0 Markdown与0#标签(6)   · 结尾大号互动CTA (5)
 · 统一杂志配色 (7)                                                                  · 合集符合白名单(4)
```

---

## Workflow

### 阶段 1：发布前专属检查清单 (Pre-flight Audit Checklist)

读取目标目录下的 `article.md` 与 `deck_spec.json`，检查 PNG 渲染图片与 SVG 源码，对照标准**直接修改文件或重绘卡片**修复问题：

```text
【图片消息 Pre-flight 检查清单】
1. 标题字数与标点零浪费（一票否决项）：
   - 提取 article.md Front Matter 的 `title` 字段。
   - 严格控制在 ≤ 20 字符（微信图片消息输入框硬顶）。
   - 严禁包含 ` ｜ `、` | `、` —— `、` - ` 及两侧空格。
   - 标点统一采用中文全角（`：`、`？`、`，`、`「」`）无空格连接。
   - 若超标或包含冗余分隔符，必须直接重构精炼为 ≤ 20 字并回写 article.md。

2. 微信摘要 120 字符硬顶（一票否决项，防微信 64703 报错）：
   - 提取 article.md Front Matter 的 `desc` 字段。
   - 严格控制在 ≤ 120 字符（微信后台 Description 字段绝对上限）。
   - 若超出 120 字符，微信后台保存接口将报 64703 错误拒绝保存；必须主动精简截断至 ≤ 120 字并回写 article.md。
   - 严禁把正文几百字长文本误填入 `desc`。

3. 伴随文案字数硬顶（一票否决项）：
   - 提取 article.md 正文纯文本（去除 front matter），统计字符数。
   - 严格控制在 350 ~ 700 字符之间，绝对禁止超过 900 字符（微信端 1000 字符硬顶）。
   - 若超长，必须主动精简删减冗余修饰，保留核心骨架与互动讨论。

4. 伴随文案段落结构与换行严审（杜绝内容粘连）：
   - 检查 `💡 核心洞察：`、`【模块标题】`、`💬 互动探讨：` 是否各自独立成行且上方保留空行。
   - 检查列表项（`• ` 或 `1. `）是否逐行独立换行，严禁小标题与列表首项合并在同一行。
   - 若发现标题与正文粘连或缺少换行，必须直接编辑 `article.md` 补全换行。

5. 0 Markdown 语法污染（移动端可读性）：
   - 正文严禁使用 `###`、`##` 等原生标题标记，小标题统一使用 `【模块标题】` 或 Emoji（如 `【为什么……】`、`💡 核心洞察：`）。
   - 正文严禁使用 `---` 分割线。
   - 正文严禁使用 `>` 引用标记，使用 `💡 核心洞察：` 引导。
   - 避免大面积使用 `**粗体**` 产生视觉噪点，强调使用中文自然标点（如「」、""）。
   - 列表项使用原生 Unicode 符号（`• ` 或 `1. `），且列表前必须保留空行。

6. 0 # 话题标签审查（一票否决项）：
   - 正文文末绝对禁止出现 `#` 话题标签（如 `#认知思维 #深度思考` 等）。
   - 微信图片消息不支持 `#` 标签超链接，堆砌标签破坏排版和谐且白白消耗字符配额。
   - 若发现文末存在 `#` 标签，必须直接整行删除并保存 `article.md`。

7. 0 LaTeX 行内公式与原生符号校验：
   - 检查正文和卡片中是否存在 `$\rightarrow$`、`$\Leftarrow$` 等 LaTeX 语法。
   - 一律自动替换为原生 Unicode 符号（`→`、`⇒`、`⚡`、`💡`、`💬`、`❌`、`✅`）。

8. 微信合集校验 (collection)：
   - `collection` 必须且只能从 `AI图文 / agent图文 / DevSecOps图文 / Web3图文 / 逻辑世界` 中选择。
   - 若不合法，自动修正为语义最贴合的合法合集。

9. 封面爆破 Hook 审查 (Cover Hook Audit)：
   - 检查 `01_cover.png`：大标题是否提炼为 4 ~ 8 字反直觉认知冲突短语？
   - 严禁在封面平铺 20+ 字的全长长句。
   - 下方必须配备 3 行高对比度微型认知冲突卡片（bad/warning/good 或核心数据对比）。

10. 卡片尺寸与比例校验：
   - 运行 `sips -g pixelWidth -g pixelHeight *.png` 校验，所有卡片必须为严格 3:4 比例（1200 x 1600 px）。
   - 严禁出现 16:9 横屏图或尺寸不一致的卡片。

11. deck_spec.json 规范与合法键名校验：
   - 校验 cards 数组各卡片的 type 与 data 字段名是否符合标准字典：
     - `cover` 必须包含 `category`, `page_idx`, `title`, `hook`, `hook_accent`, `subtitle`, `stats`（子项含 `badge`, `val`, `note`, `type`）。
     - `vs_comparison` 必须包含 `left_col`, `right_col`（子项含 `badge`, `title`, `items: [{title, desc}]`）, `bottom_takeaway`。
     - `bullet_points` 必须包含 `points`（子项含 `badge`, `title`, `desc`, `tags`），严禁误写为 `items`。
     - `pipeline_steps` 必须包含 `steps`（子项含 `step_num`, `title`, `desc`, `deliverables`）, `bottom_rule`。
     - `summary_cta` 必须包含 `checklist`, `cta_title`, `cta_question`, `action_bar`。

12. 移动端字号硬底线与防溢出排查 (Typography & Clipping Audit - CRITICAL)：
   - 大标题 / Hook：`56px ~ 72px`
   - 模块标题 / 核心节点：`34px ~ 42px`
   - 正文要点 / 节点说明 / 标签：严格禁止低于 `28px`（标签与辅助说明 ≥ `24px`）。
   - 【边缘溢出排查】：
     - 在 `vs_comparison` 双栏卡片中，每栏宽度仅 510px，单行文字严禁超过 13 个中文字符，否则会导致右侧文字被边框截断。发现溢出时必须精炼为短语。
     - 在 `bullet_points` 卡片中，描述文字控制在 2 行以内（每行 ≤ 26 字）。
     - 在 `pipeline_steps` 卡片中，Step 标题与交付物文字必须留有 24px+ 右侧安全边距。
     - 在 `summary_cta` 卡片中，互动提问过长时必须显式拆为两行。

13. 0 工具固定水印与样板词审查 (Zero Boilerplate Watermark Audit)：
   - 卡片头部徽章旁绝对禁止出现未配置时的默认 `AGENT` 或 `@AGENT`。
   - 卡片底部左侧绝对禁止出现 `BLOGGER AGENT` 工具水印与硬编码固定文字。
   - 确保卡片呈现 100% 干净专业的原生阅读视觉。

14. AI 绘图 0 俗套审查（若首图为 AI 生成）：
   - 画面 100% 杜绝发光蓝脑、机械手、科幻 HUD、乱码假字。
   - 严格遵循 5 大杂志社论艺术风格（扁平插画 / 实体机械隐喻 / 清晰线稿 / 等轴黏土 / 包豪斯）。

15. 互动探讨 CTA (Discussion Trigger)：
   - 文末及卡片最后一张（`summary_cta`）必须包含面向读者的启发性争议提问（`💬 互动探讨：`），以引导评论区互动提升公域推荐权重。
```

---

### 阶段 2：卡片排版修复与自动化重绘 (Auto-Fix & Re-render)

若在检查过程中发现卡片存在文字溢出、字号过小或描述冗长：
1. 直接编辑目标目录下的 `deck_spec.json`。
2. 使用 `generate_photo_cards.py` 重新渲染 PNG 卡片：

```bash
uv run python tools/generate_photo_cards.py --config articles/YYYY-MM-DD-photo-<slug>/deck_spec.json --output-dir articles/YYYY-MM-DD-photo-<slug>/
```

3. 使用 `sips` 校验输出尺寸确保 1200x1600。

---

### 阶段 3：文案精炼与报告输出

1. 直接编辑修改 `article.md`，确保字符数在 350 ~ 700 字符内，0 Markdown 标记污染。
2. 输出专属 100 分制打分卡与审查总结，明确告知主叫方是否通过（PASS / FAIL）以及具体修复项。
