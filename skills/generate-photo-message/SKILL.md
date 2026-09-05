---
name: generate-photo-message
description: Use when the user asks to create, design, or publish a WeChat Photo Message (图片消息 / 小绿书图文 / 微信画册 / 竖版知识卡片), or explicitly invokes `/generate-photo-message` or `/photo-message`. Trigger phrases include "生成图片消息", "制作图片消息", "发小绿书", "做小绿书图文", "微信图片消息", "图文卡片", "切片做成图片消息". It produces a 3:4 vertical high-resolution card deck (1200x1600) and structured markdown copy. Once drafted, it MUST dispatch a subagent to review the assets.
---

# Generate Photo Message Skill (微信图片消息 / 小绿书制作)

## Overview

把任意输入（热点洞察、长文切片、深度观点、技术架构、实战方法论）转化为**高点击率（High CTR）、3:4 竖版高密排版、极简短语化、直通公域推荐池**的微信图片消息（小绿书/微信画册） Payload。

微信官方对“图片消息”给予极高的**公域算法推荐权重**（“看一看”、订阅号消息瀑布流卡片推荐、“搜一搜”）。本 Skill 是专门针对此形态打造的**视觉分镜建模 + 爆破文案编排 + 批处理自动化渲染**一体化流水线。

---

## 核心战略与底层哲学：7:3 漏斗与三大链路

### 1. “7:3 漏斗”公域增长模型 (Funnel Strategy)
- **70%~80% 兵力（图片消息 = 公域爆破手）**：单手滑阅、卡片即视感、高完播率（70%+）与高收藏率，天然击中微信算法冷启动推流机制，用于公域获客、爆款涨粉与高频敏捷试错。
- **20%~30% 兵力（深度长文 = 信任沉淀池）**：依靠搜一搜长尾沉淀、多平台同步（CSDN/掘金），建立专家声誉与高信任商业转化。

### 2. 三大流水线生产范式 (3 Pipeline Archetypes)
1. **原生破圈快打链路 (Topic-to-Deck Native)**：
   - 捕捉行业冲突或反常识认知 ➔ 提炼 4~8 字爆破 Hook ➔ 规划 5~6 张分镜卡片 ➔ 撰写 500 字精炼导读 ➔ 批处理渲染发布。
2. **深度长文切片提炼链路 (Long-to-Deck Slicing)**：
   - 摄取已有长文（`articles/published/` 或最新长文） ➔ 抽取 1 组矛盾对抗 + 3 大核心支柱 + 1 个避坑 SOP ➔ 快速生成切片图片消息，文末引导阅读长文全貌。
3. **爆款逆向反哺链路 (Deck-to-Long Expansion)**：
   - 监测图片消息数据，当某篇图文在评论区产生激烈探讨或获大量推流 ➔ 顺势扩写为技术全景长文或专题合集。

### 3. 4 大硬核业务假设
- **【极化爆破钩子假设】(Hook Dissonance)**：首图决定 80% 点击率，封面大标题必须提炼为 **4 ~ 8 字认知冲突短语**（如 `0.99刀的真相？`、`穿仓的必然性`），CTR > 10%。
- **【3:4 竖版高密画册假设】(Visual Density Floor)**：统一采用移动端黄金比例 **3:4**（`1200 x 1600 px`），字号严禁低于 28px，拒绝整段长文。
- **【高互动算法放大假设】(Algorithm Amplification)**：微信推流最看重“完读率、收藏率、评论互动率”，文末与尾卡必须配置**强互动争议 CTA**，撬动评论区裂变。
- **【T-A-O 认知协作架构】(Orchestration)**：人类负责 Context Framing（高维问题与冲突提炼）；AI 负责卡片建模、SVG 矢量绘制与批处理高清渲染。

---

## 📱 移动端优先（Mobile-First）排版与平台安全红线（CRITICAL）

微信图片消息发布接口有严苛的长度与排版限制，必须严格遵守以下红线以确保 100% 发布成功且具有顶级移动端阅读质感：

### 1. 标题 20 字符硬顶与标点零浪费（Strict ≤ 20 字符，CRITICAL）
- **20 字符绝对红线**：Front Matter 的 `title` 必须严格控制在 **≤ 20 字符**（推荐 12 ~ 18 字符），超出将被微信接口截断或报错。
- **标点零浪费与空格清零**：**严禁使用 ` ｜ `、` | `、` —— `、` - ` 及两侧空格**！统一使用中文全角标点（`：`、`？`、`，`、`「」`）无空格连接。
- **4 大极简爆款标题范式**：
  - ① 设问冲突型：`[设问短语？][核心定论/真相]`（如 `冥想是空耗时间？大脑正在信息戒断` - 17字）
  - ② 钩子冒号型：`[爆破词]：[解法/商业本质]`（如 `0.99刀真相：揭秘域名暴利定价` - 15字）
  - ③ 反直觉警示型：`[警示痛点]，[破局手段]`（如 `别死磕语法：成人英语极简自测法` - 16字）
  - ④ 单句高张力直击：一句话穿透核心利益点（如 `为什么顶尖AI都在做模型蒸馏` - 14字）

### 2. 微信摘要 120 字符硬顶与字段解耦（Summary ≤ 120 字符，CRITICAL）
- **致命后台陷阱**：微信后台保存接口（`operate_appmsg`）对摘要输入框（`textarea#js_description`）设有 **120 个字符的绝对上限**。超出 120 字符微信服务器直接报错拒绝保存：`{"err_msg": "Summary has exceeded the maximum of 120 Chinese characters", "ret": 64703}`。
- **字段解耦防混淆**：
  - `desc` 对应摘要输入框，必须控制在 **60 ~ 120 字符** 内，严禁超标！
  - 伴随文案（正文）对应富文本流（上限 1000 字），**绝对禁止把几百字正文写入 `desc`**。

### 3. 伴随文案字符硬顶（Strict 350 ~ 700 字符，上限绝对 ≤ 900 字符）
- 伴随文案是“导读与互动引流”，**严禁把长文全盘堆砌进伴随文案**。
- 纯文本字符数（含 Emoji、空格、标点）严格控制在 **350 ~ 700 字符之间**，**绝对禁止超过 900 字符**（微信端上限 1000 字符，预留标签冗余）。

### 4. 轻量小绿书文案排版（No Markdown Clutter & No Hashtags）
- 禁用 `###`、`##` 等原生 Markdown 标记，段落小标题统一使用 `【模块标题】` 或 Emoji 引导（如 `【一、痛点与现实困境】`、`📌 核心支柱`）。
- 禁用 `---` 分割线。
- 引用统一使用 `💡 核心洞察：` 引导行，禁用 `>` 语法。
- 列表项使用原生 Unicode 符号（`• ` 或 `1. `）。
- 强调使用自然标点（如「」、“”），避免大面积使用 `**粗体**` 产生字符噪点。
- **严禁文末堆砌 `#` 话题标签**：微信图片消息不支持 `#` 标签超链接，文末堆砌 `#标签` 会破坏视觉排版并浪费字数；文末以 `💬 互动探讨：` 优雅收尾。

### 5. 伴随文案段落结构与换行铁律（Linebreak & Paragraph Layout, CRITICAL）
微信图片消息输入框底层将文案作为单个 ProseMirror 流解析，两个换行 `\n\n` 会被映射为 `<br><br>`：
- **核心洞察独占段落**：`💡 核心洞察：...` 作为开篇导读，独占一段，下方必须留空行。
- **模块小标题必须独占一行**：`【模块标题】` 必须单占一行，且上方必须保留空行。**严禁小标题与后文正文或列表第 1 项挤在同一行**！
- **列表项逐行独立**：每一个 `• ` 或 `1. ` 列表要点必须独立换行，保证移动端纵向清晰阅读流。
- **互动探讨独立成段**：`💬 互动探讨：` 作为结尾卡片，上方必须留空行，引导行独占一行，下方紧随互动提问。

### 6. 4 大高互动 CTA 范式（撬动算法评论推流）
在文末及尾卡（`summary_cta`）中配置争议/互动钩子，提升推流转化：
- **范式 1：站队抉择型**：`在成本直降 80% 但偶尔需要人工复核的情况下，你会选择立即切换还是继续观望？`
- **范式 2：账本与晒坑型**：`你买过最划算/最后悔的域名是多少钱？在续费或托管中踩过哪些隐形账单深坑？`
- **范式 3：实战索取型**：`如果你也正在搭建长程编码自愈流水线，需要文中同款评测脚本与 Prompt 的，欢迎在评论区交流讨论！`
- **范式 4：认知反思型**：`你的团队是否也陷入了“以为买最贵模型就能解决复杂业务”的虚假安全感？`

### 7. 移动端字号硬性底线（Mobile Typography Floor）
- **大标题 / Hook 核心词**：`56px ~ 72px`（超粗加重，8字以内爆破短语）
- **模块标题 / 核心节点**：`34px ~ 42px`
- **正文要点 / 节点说明 / 标签**：**严格禁止低于 26px ~ 28px**！在 1200px 宽度的 3:4 卡片中，缩放至手机屏幕（360px）时缩放比仅 0.30，低于 26px 的文字会缩水为 <7.8px 的模糊小点。
- **极致短语化**：卡片节点文字控制在 **4 ~ 8 个字以内**（短语化、符号化、加粗关键词如 `第一性原理 · 边界审计`）。**严禁在卡片中堆砌整段长句**。

### 8. 统一原生符号（No LaTeX）
- 严禁在图表或文案中使用 LaTeX 公式（如 `$\rightarrow$`），必须直接使用原生 Unicode 符号（`→`, `⇒`, `❌`, `✅`, `⚡`, `💬`, `⭐`）。


---

## 🎨 3:4 封面设计三大模式与多模态策略

为避免整套卡片从头到尾清一色冷色框图，首图（`01_cover.png`）支持 3 大封面模式：

### 模式 A (默认)：SVG 复合杂志信息卡片 (`photo_card_generator.py`)
- **适用**：硬核系统、逻辑拆解、方法论清单。
- **结构**：顶部大字号爆破 Hook（68px） + 副标题（32px） + 3 行高对比度认知冲突微型卡片（36px+28px）。

### 模式 B：AI 具象概念场景隐喻封面 (`generate_image` 3:4 比例)
- **适用**：反直觉认知、重型 vs 轻量对抗、哲学反思、爆款破圈。
- **生成方式**：调用 `generate_image`（设置 `AspectRatio: "3:4"`），使用 **5 大去 AI 味杂志社论流派**（杜绝发光脑、机械手、科幻 HUD、乱码假字），生成高审美具象物理隐喻画面。
- **5 大流派 Prompt 模板**：
  1. **现代社论扁平插画**：`Modern editorial vector illustration, 3:4 vertical poster, flat 2D graphic design, elegant bold silhouettes, clean textured geometry, contemporary magazine style, subtle paper texture, cohesive color palette of slate gray, amber and deep navy. Scene depicting [具体场景]. No text, no words.`
  2. **实体机械/物理隐喻对比**：`Conceptual physical metaphor illustration, 3:4 vertical composition, vintage intricate mechanism contrasting with sleek modern minimalist artifact, rich tactile textures, warm atmospheric cinematic lighting. Scene showing [具体物理对比]. No text, no glowing sci-fi clichés.`
  3. **复古清晰线稿与版画 (Ligne Claire)**：`Ligne claire illustration style, Moebius inspired ink line art with subtle watercolor wash, 3:4 vertical layout, matte muted earth tones (terracotta, olive green, cream paper). Scene showing [具体场景]. Zero text.`
  4. **等轴测微缩黏土模型**：`Isometric stylized miniature diorama, 3:4 vertical composition, handcrafted matte clay and folded paper aesthetic, soft tactile studio lighting, mint green and cream harmony. Scene showing [微缩系统场景]. No text.`
  5. **包豪斯构成主义**：`Bauhaus constructivist graphic art, 3:4 vertical poster, Swiss typographic style, bold abstract geometric forms, diagonal dynamic balance, matte screen print texture. Concept representing [抽象力学平衡]. No text.`

### 模式 C：NotebookLM 便当网格与深度信息卡片 (`generate-infographic` 技能)
- **适用**：多模块全景架构、高信息密度知识卡片、切片核心机制长图。
- **生成方式**：调用 `generate-infographic` 技能（`uv run notebooklm generate infographic --style bento-grid --orientation portrait --detail detailed "Prompt" --json` 或 `uv run blogger infographic`），将长文/切片直接提炼为 3:4 竖版便当网格（Bento Grid）或社论长图，作为 Deck 的核心深度卡片（如 `02_infographic.png`）。

---

## 🛠️ Required Tools

- **高维知识长图引擎**：`generate-infographic` 技能（基于 Google NotebookLM `uv run notebooklm generate infographic`，生成 3:4 竖版 Bento-grid/Editorial 高密信息图）。
- **原生卡片渲染引擎**：`tools/generate_photo_cards.py`（支持单张或通过 JSON/YAML 配置批量生成）。
- **底座模块**：`src/blogger/core/photo_card_generator.py`（内置 5 大布局模板与 4 款杂志级主题配色）。
- **AI 绘图工具**：`generate_image`（支持 3:4 竖版具象概念隐喻封面生成）。
- **转换工具**：macOS 原生 `sips`（配合 `--resampleWidth 1200` 实现 Retina 级别清晰度，零锯齿与发虚）。
- **文件系统**：管理 `articles/YYYY-MM-DD-photo-<slug>/` 目录结构。

---

## 6 大经典卡片模板矩阵

| 模板标识 | 适用场景 | 关键视觉要素 |
|---|---|---|
| **`cover`** | 首图 Hook / 封面 | 分类 Badge + 4~8 字爆破短语 (68px) + 副标题 (32px) + 3 行微型数据/认知对比卡 (36px/28px) + 滑动提示 |
| **`bento_infographic`** | 全景知识便当图 / 核心机制长图 | **通过 `generate-infographic` 生成**：便当盒模块化网格、高信息密度提炼、3:4 竖版大图 |
| **`vs_comparison`** | 二元对抗 / 新旧对比 | 双栏对比矩阵（左侧 ❌ 传统旧模式 vs 右侧 ✅ 现代新范式） + 底部核心结论条 (28px) |
| **`bullet_points`** | 核心支柱 / 模块清单 | 3~4 个独立圆角卡片，含序号 Pill、加粗要点 (36px)、短语描述 (28px) 与底部标签组 (24px) |
| **`pipeline_steps`** | 步骤流转 / 工程链路 | 垂直连线流转卡片（Step 01 → Step 02 → Step 03） + 阶段交付物 (26px) + 底部铁律栏 (26px) |
| **`summary_cta`** | 复盘清单 / 互动引流 | 3~4 项核心 Checklist (28px) + 突出的大号互动探讨卡片（💬 提问 34px） + 点赞/收藏/转发栏 (26px) |


---

## 🎨 4 套杂志级主题配色与合集字典

### 4 大主题色板
- **`navy_gold`**（黑曜曜石蓝 `#0F172A` + 琥珀金 `#F59E0B`）：**首选**。硬核技术、AI 架构、金融量化、系统工程。
- **`swiss_red`**（极简白底 `#F8F9FA` + 瑞士红 `#E63946`）：经典社论、犀利观点、反直觉认知、认知破局。
- **`emerald`**（深邃森林绿 `#022C22` + 薄荷绿 `#10B981`）：工程效能、增长飞轮、开源生态、敏捷治理。
- **`slate_lime`**（暗黑哑光灰 `#18181B` + 荧光青柠 `#84CC16`）：开发者工具、系统底层、黑客极客、基础设施。

### 微信内置合法合集 (photo_collections)
在 Front Matter 中填写的 `collection` **必须且只能**为以下 5 个之一（严格映射自 `blogger.toml`）：
1. `AI图文`
2. `agent图文`
3. `DevSecOps图文`
4. `Web3图文`
5. `逻辑世界`

---

## 📊 `deck_spec.json` 5 大卡片模板标准字典 (CRITICAL SPEC)

渲染引擎 `tools/generate_photo_cards.py` 驱动 5 大核心模板。在编写 `deck_spec.json` 时，**必须严格遵守以下键名与层级结构**，严禁臆造字段名：

```json
{
  "theme": "navy_gold",
  "cards": [
    {
      "name": "01_cover",
      "type": "cover",
      "data": {
        "category": "AI BENCHMARK",
        "page_idx": "01 / 05",
        "title": "Flash战平Opus5？",
        "hook": "Flash战平Opus5？",
        "hook_accent": "长程工程模型倒挂",
        "subtitle": "揭秘 Gemini 3.8 Flash 越级打平旗舰的能效革命",
        "stats": [
          {
            "badge": "工程评测打平 ⚡",
            "val": "DeepSWE 73.7% vs 74.0%",
            "note": "长程软件工程能力几乎持平 Opus 5",
            "type": "good"
          },
          {
            "badge": "单任务成本降 80% 💰",
            "val": "任务成本仅需 $1.8",
            "note": "仅为 Opus 5 ($8.5) 的五分之一",
            "type": "good"
          },
          {
            "badge": "客观能力边界 ⚠️",
            "val": "GUI 与复杂知识仍有差距",
            "note": "OSWorld 电脑操作与复杂知识仍是 Opus 5 占优",
            "type": "warning"
          }
        ]
      }
    },
    {
      "name": "02_vs_comparison",
      "type": "vs_comparison",
      "data": {
        "category": "PARADIGM SHIFT",
        "page_idx": "02 / 05",
        "title": "认知重构：旧模式 vs 新范式",
        "subtitle": "为什么高昂单次调用正在被高频低成本闭环取代？",
        "left_col": {
          "badge": "传统旧模式 ✕",
          "title": "重型旗舰单兵",
          "items": [
            { "title": "单任务成本极高 ($8.5)", "desc": "限制多智能体并行探索与重试" },
            { "title": "Token 定价昂贵 ($25/M)", "desc": "多轮长程推演快速吞噬预算" },
            { "title": "单次生成依赖度过大", "desc": "首轮出错后回溯排查成本陡增" }
          ]
        },
        "right_col": {
          "badge": "现代新范式 ✓",
          "title": "轻量高能效智能体",
          "items": [
            { "title": "极低单任务成本 ($1.8)", "desc": "同等预算支持 5 倍并发与自愈" },
            { "title": "DeepSWE 73.7% 战平旗舰", "desc": "长程软件工程与终端能力越级" },
            { "title": "工业级密集自愈循环", "desc": "完美契合编码智能体自愈闭环" }
          ]
        },
        "bottom_takeaway": "底层逻辑改变：决胜点不再是单一重型模型，而是能效驱动的自愈闭环。"
      }
    },
    {
      "name": "03_bullet_points",
      "type": "bullet_points",
      "data": {
        "category": "KEY BENCHMARKS",
        "page_idx": "03 / 05",
        "title": "越级反超的三大硬核战场",
        "subtitle": "从防污染真实基准透视能力跃迁与工程边界",
        "points": [
          {
            "badge": "BENCHMARK 01",
            "title": "长程代码自愈：DeepSWE 73.7%",
            "desc": "在 113 个高难开源任务中与顶级旗舰打平，代码生成准确度越级跳升。",
            "tags": ["软件工程", "代码自愈", "打平旗舰"]
          },
          {
            "badge": "BENCHMARK 02",
            "title": "终端控制闭环：Terminal 89.4%",
            "desc": "复杂命令行环境下具备高容错率，自主识别并纠正语法错误。",
            "tags": ["CLI Agent", "环境感知", "高容错"]
          },
          {
            "badge": "BENCHMARK 03",
            "title": "极速响应：动态思考算力弹性按需调配",
            "desc": "根据任务复杂度自主伸缩思维链步长，兼顾单字生成与深层推理。",
            "tags": ["动态思考", "高能效比", "工业落地"]
          }
        ]
      }
    },
    {
      "name": "04_pipeline_steps",
      "type": "pipeline_steps",
      "data": {
        "category": "IMPLEMENTATION",
        "page_idx": "04 / 05",
        "title": "生产落地避坑四步实施路径",
        "subtitle": "从评测到工业级流水线部署的工程化最佳实践",
        "steps": [
          {
            "step_num": "01",
            "title": "基准对齐与任务分级",
            "desc": "将轻量自愈任务与复杂 GUI/超长推理任务严格分类打标。",
            "deliverables": ["任务分级表", "基准测试集"]
          },
          {
            "step_num": "02",
            "title": "双轨并发路由配置",
            "desc": "80% 常见循环交由 Flash 承担，20% 重型推演兜底路由至旗舰。",
            "deliverables": ["路由决策网关", "成本熔断策略"]
          },
          {
            "step_num": "03",
            "title": "自动重试与自愈闭环",
            "desc": "利用 Flash 的低成本优势开放 3~5 次重试机会，以重试代慢想。",
            "deliverables": ["自愈执行器", "单元测试校验器"]
          },
          {
            "step_num": "04",
            "title": "能效与 ROI 持续看板监控",
            "desc": "实时监控单任务花费与通过率，保持系统在最优能效象限。",
            "deliverables": ["Grafana 看板", "成本对账单"]
          }
        ],
        "bottom_rule": "工程铁律：永远用 1/5 成本的 5 倍并发验证，对抗高昂单次旗舰幻觉。"
      }
    },
    {
      "name": "05_summary_cta",
      "type": "summary_cta",
      "data": {
        "category": "TAKEAWAY & CTA",
        "page_idx": "05 / 05",
        "title": "核心复盘与互动探讨",
        "subtitle": "轻量能效革命带来的选型重构与行动清单",
        "checklist": [
          "摆脱旗舰迷信：优先评测高性价比轻量模型真实场景表现",
          "构建自愈闭环：以高频低成本验证替代低频昂贵单点生成",
          "双轨工程混布：轻量模型干重活，旗舰模型只负责复杂推理兜底"
        ],
        "cta_title": "💬 互动探讨：你的选型考量？",
        "cta_question": "在智能体工程落地中，你更看重单次推理的极致上限，还是 1/5 成本带来的 5 倍并发探索验证？欢迎在评论区分享你的实战考量！",
        "action_bar": "SWIPE · LIKE · COMMENT · SAVE"
      }
    }
  ]
}
```

---

## Standard Workflow (SOP)

执行任务时**必须按顺序**走完以下 4 个阶段。

---

### 阶段 1：分镜大纲与双重自检（实质 + 形式）

在生成任何图片或 Markdown 之前，**必须在回复中输出以下两份自检并填答**：

#### A. 内容质量自检
```text
【图片消息内容质量自检】
1. 爆破 Hook（4-8字）：封面击穿读者哪个固有偏见？（如：0.99刀的真相？/ 穿仓的必然性）
2. 社交货币命名实体：本文提炼了哪 1 个具备传播力的概念/方法论？（如：1.111B Class / 动态自愈路由）
3. 3~6 张卡片分镜规划（支持 SVG 卡片与 NotebookLM 便当网格混编）：
   - 卡片 01 (cover)：爆破 Hook + 核心冲突数据（或 AI 具象概念隐喻封面）
   - 卡片 02 (vs_comparison / bento_infographic)：新旧范式二元对抗或全景架构长图
   - 卡片 03 (bullet_points)：三大支柱 / 关键越级机制拆解
   - 卡片 04 (pipeline_steps)：四步落地实施链路 / 避坑 SOP
   - 卡片 05 (summary_cta)：Checklist 闭环 + 1 个评论区强争议互动问题
```

#### B. 形式与安全自检
```text
【形式自检】
- 标题长度：严格 ≤ 20 字符（推荐 12 ~ 18 字符），严禁包含 ` ｜ `、` —— `、` - ` 及两侧空格。
- 摘要长度 (desc)：严格 60 ~ 120 字符，绝对禁止超过 120 字符（防止微信 64703 错误）。
- 画布比例：严格 3:4 竖版（1200 x 1600 px）。
- 字号底线：大标题 56-72px，卡片标题 ≥ 34px，正文节点严格 ≥ 28px（标签/辅助 ≥ 24px），无整段长句堆砌。
- 配色主题：统一从 navy_gold / swiss_red / emerald / slate_lime 中选取 1 种。
- 0 工具固定水印与样板词：卡片头部 0 默认 AGENT，底部 0 BLOGGER AGENT 水印，保持纯净排版。
- 0 AI 俗套审查：若使用 AI 绘图生成封面，绝无发光蓝脑、机械手、科幻 HUD、乱码假字。
- 微信合集 collection：必须且只能从 AI图文 / agent图文 / DevSecOps图文 / Web3图文 / 逻辑世界 中选择。
- 伴随文案字数：严格控制在 350 ~ 700 字符（上限绝对 ≤ 900 字符），0 Markdown 语法污染。
- 伴随文案排版：小标题【...】与引导语独立成行且上方留空行，列表项逐行独立，0 内容粘连。
- 0 #话题标签：严禁在文末堆砌 # 话题标签，文末以 💬 互动探讨 优雅收尾。
- 符号规范：100% 使用原生 Unicode 符号，0 LaTeX 行内公式。
```

---

### 阶段 2：文图双轨协同撰写 (`deck_spec.json` & `article.md`)

1. **创建 Payload 目录**：
   `articles/YYYY-MM-DD-photo-<slug>/`（如 `articles/2026-09-03-photo-gemini-3-8-flash`）。

2. **撰写卡片配置 `deck_spec.json`**：
   参考上文的标准模板字典，在目标目录下创建 `deck_spec.json`，确保数据与分镜一致。

3. **撰写伴随文案 `article.md`**：

#### Front Matter 规范 (CRITICAL)
```yaml
---
title: "Flash战平Opus5？揭秘成本倒挂" # 严格 ≤ 20 字符，无 ｜ 或 ——
author: "Agent"
desc: "Gemini 3.8 Flash 斩获 73.7% 战平旗舰 Claude Opus 5，任务成本直降 80%。深度拆解基准跑分、能效革命与工程选型边界。" # 严格 ≤ 120 字符
type: "photo" # 声明为图片消息
collection: "AI图文" # 必须且只能从 photo_collections 选取
creation_source: "个人观点，仅供参考" # 可选，支持：个人观点，仅供参考 / 内容由AI生成
tags: ["人工智能", "软件工程", "大模型", "架构设计"]
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
# Flash战平Opus5？揭秘成本倒挂

💡 核心洞察：轻量级模型只能当总结玩具？真实评测击碎了这一偏见：在严苛的长程软件工程评测 DeepSWE v1.1 中，以 73.7% 的战绩几乎打平行业旗舰 Claude Opus 5（74.0%），而单次任务成本直接暴跌 80%。

【三大硬核基准：越级反超】
• 软件工程 DeepSWE：在防训练污染的 113 个真实开源任务中斩获 73.7%，打平 Opus 5（74.0%），远超 Sonnet 5。
• 终端编码与自愈：Terminal-bench 取得 89.4%，并在智能体评测中领先。
• 能效前沿临界点：单任务成本仅约 $1.8，对比 Opus 5 的 $8.5 节约近五分之四。

【理性看待边界：两类任务仍需旗舰】
必须客观指出，系统级电脑操作（OSWorld 75.4% vs 59.0%）与复杂开放知识推理中旗舰依然保持优势。合理的工程架构是用 Flash 承担高频代码自愈与终端循环，将 GUI 操作交由专精模型。

💬 互动探讨：
在你的开发与智能体落地中，更看重单次推理的极致上限，还是 1/5 成本带来的 5 倍并发验证？欢迎在评论区分享你的选型考量！
```

---

### 阶段 3：批处理卡片渲染与多模态整合

1. **批处理生成卡片**：
   ```bash
   uv run python tools/generate_photo_cards.py --config articles/YYYY-MM-DD-photo-<slug>/deck_spec.json --output-dir articles/YYYY-MM-DD-photo-<slug>/
   ```

2. **（可选）NotebookLM 便当长图合成**：
   若包含全景架构图，调用 `generate-infographic` 技能生成 3:4 竖版便当图覆盖对应卡片：
   ```bash
   uv run blogger infographic \
     --prompt "提炼全景机制：顶部呈现痛点，中部 3 栏核心机制，底部 3 个避坑 Checklist" \
     --style bento-grid \
     --orientation portrait \
     --output articles/YYYY-MM-DD-photo-<slug>/02_infographic.png
   ```

3. **尺寸与分辨率极验**：
   ```bash
   sips -g pixelWidth -g pixelHeight articles/YYYY-MM-DD-photo-<slug>/*.png
   ```
   确保所有卡片均为 `1200 x 1600`，且文件名按 `01_cover.png`、`02_xxx.png` 依序排列。

---

### 阶段 4：Dispatch Review (Subagent)

**CRITICAL INSTRUCTION**: 卡片与文案生成完成后，**严禁直接发布**。
你必须调用子代理（`@self`）并指示其使用专属审查技能 `review-photo-message`（或按专属 100 分制打分卡）进行终审：
- 标题是否严格 **≤ 20 字符**，且 100% 杜绝 ` ｜ `、` —— `、` - ` 及两侧空格？
- 摘要 `desc` 是否严格 **≤ 120 字符**（一票否决项，防 64703 错误）？
- 伴随文案纯文本字符数是否严格在 **350 ~ 700 字符** 且 **≤ 900 字符**？
- 伴随文案排版：小标题【...】、💡洞察、💬互动探讨是否各占独立行并正确换行，列表项是否逐行独立，无段落粘连？
- 0 #话题标签：正文文末是否 0 # 标签堆砌？
- 卡片是否为严格 3:4 比例（1200x1600 px）？
- 卡片中是否 0 默认 AGENT 标记与 0 BLOGGER AGENT 固定水印？
- 移动端字号是否全部严格 ≥ 28px（核心节点 ≥ 34px，标签/辅助 ≥ 24px）且无文字边缘截断/溢出？
- 封面是否有 4~8 字爆破 Hook 与 3 行高对比微型认知卡？
- 若首图为 AI 生成，是否 100% 杜绝了发光蓝脑、机械手、科幻 HUD、乱码假字？
- 正文是否为 0 LaTeX 公式、0 Markdown 语法污染（无 `###`、`---`、`**`）？
- `collection` 是否严格属于 `AI图文 / agent图文 / DevSecOps图文 / Web3图文 / 逻辑世界`？

审查通过后，即可提示用户使用 `/publish-article` 进行推送！


