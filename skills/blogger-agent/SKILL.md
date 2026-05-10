---
name: blogger-agent
description: Use when the user asks to write a technical article, blog post, or WeChat draft, or to publish/share content to Chinese platforms (微信公众号 / 掘金 / CSDN). Trigger phrases include "写一篇文章""整理成博客""发到公众号""帮我发个草稿""推送到掘金/CSDN". The skill produces a Markdown payload directory (front matter + 正文 + 配图) and invokes the `blogger` CLI to push the draft.
---

# Blogger Agent

## Overview

把任意输入（草稿、对话、观点、技术笔记）转化为**结构清晰、论点锐利、图文绑定**的中文技术文章，生成插图与封面，调用本地 `blogger` CLI 推送到主流博客平台。

与浏览器自动化不同，此 skill 走的是「Markdown payload + CLI」管道。本 skill 同时是**创作助手 + 编辑助手**：它会逼你先想清楚「主张是什么」「证据是什么」，再开写；写完后强制做一次反 AI 腔自审。所有发到微信公众号的文章会自动把"创作声明"设为"个人观点，仅供参考"。

## When NOT to use

- 用户只想让你**改稿、提建议、做大纲**——不要直接走全流程发布，回到对话即可。
- 用户没有指明"发到/推送到"某平台、也没有说"整理成文章"——可能只是闲聊或问问题。
- 用户想发到非中文博客平台（Medium、dev.to 等）——本 skill 不支持，告知用户。

## Prerequisites（启动前必查，跳过会在阶段 5 报错）

发布前依赖三件事，任何一项缺失都会导致 `blogger` CLI 中途崩溃且报错信息不够直白。**首次进入阶段 2 之前**先帮用户确认：

1. **Chrome 必须开启「允许 Apple 事件中的 JavaScript」**（默认关闭）——CLI 走 osascript 调 JS 操作微信编辑器，开关没开会抛 `通过 AppleScript 执行 JavaScript 的功能已关闭`。让用户去 **Chrome 菜单栏 → View / 查看 → Developer / 开发者 → Allow JavaScript from Apple Events / 允许 Apple 事件中的 JavaScript**，勾上即可。
2. **Chrome 当前已登录微信公众号后台**（任意 tab 打开 `mp.weixin.qq.com` 即可）。CLI 会自动复用已有 session，未登录就只能让用户先去登录一次。
3. **本地渲染工具就位**：`~/bin/mmdc`、`~/bin/plantuml.jar`、`rsvg-convert`、`python3 + Pillow + matplotlib`。缺则按"附录：本地渲染工具一次性安装"补齐。

> ⚠️ 这三条只需问一次。如果用户上次发布过、本次同会话里再发布，可以默认前置都满足。

## Required Tools

- **bash**：跑 `blogger` CLI 与图片生成子进程。
- **文件系统**：建 Payload 目录、保存图片与 Markdown。
- **图片生成**（按内容类型分工，参数详见阶段 2）：
  - **角色 / 场景化封面、概念意象图**：原生 AI 绘图工具（如 `generate_image`）。
  - **排版式封面（书评 / 杂志风）**：Python `matplotlib`（无 AI 绘图工具时的兜底）。
  - **结构化图表（架构 / 流程 / 拓扑 / 思维导图 / UML）**：本地离线渲染优先：
    - `~/bin/mmdc`（官方 `@mermaid-js/mermaid-cli`，Puppeteer + Dagre 布局，**Mermaid 首选**）
    - `~/bin/plantuml.jar`（PlantUML，配合 `!pragma layout smetana` 无需 Graphviz）
  - **最后兜底**：`blogger generate-diagram --type mermaid|plantuml --input x --output x.png`（kroki.io，受公网限制，仅本地工具不可用时使用）
  - 工具未安装时按"附录：本地渲染工具一次性安装"自助安装，不要回退到只用 kroki。
- **封面 letterbox 工具**：`~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py`（随 skill 分发）——把任意比例的封面 letterbox 到目标比例（默认 16:9，可选 1:1 / 2.35:1），支持 `--bg white|black|auto|#RRGGBB` 与 `-o/--output` alias。详见 §2.3。

## Workflow

执行发布任务时**必须按 5 阶段顺序**走完，每一步都不可跳过。

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

4. 文章类型：这是哪种文章？(选一个，决定阶段 3 的结构)
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
- 正文配图 1–3 张，每张图必须在文中被显式引用并解释，不能孤儿。
```

---

### 阶段 2：视觉资产生成

依据阶段 1 的「证据清单」与文章类型，规划配图。**第一步永远是 §2.0 素材盘点——先看用户给了什么**，再决定要不要新生成。

#### 2.0 素材盘点：先看用户给了什么（在生成任何新图之前）

用户经常会随消息附带图片：UI 截图、产品照、自己画的草图、终端输出。**这些往往是最有力的一手证据——比 AI 生成图更可信、比 Mermaid 重画更贴合现场**。在调用 mmdc / matplotlib / `generate_image` 之前，先做以下四步：

1. **列清单**：把会话里出现过的每张图过一遍，用 `Read` 多模态打开看清楚，记下"画的是什么 + 类型"（UI 截图 / 产品图 / 终端输出 / 手绘 / 表情包 / 照片）。
2. **逐张定用途**：
   - **当正文配图**：截图、产品图、终端输出、用户手绘流程图——拷进 Payload 目录，按 §2.1 语义化命名规则重命名（`claude-code-task-list.png`，**不是** `IMG_2024.png` 或 `Screenshot_20260508.png`），在对应小节用 `![图注：...](xxx.png)` 引用。
   - **当封面**：构图横向、视觉冲击强、扣题——重命名为 `cover.png`，按 §2.3 规范 letterbox 到 **16:9**（横向内容）或 **1:1**（视觉/海报型）。
   - **跳过**：模糊 / 跑题 / 含敏感信息（token、API key、个人邮箱、同事头像、内部路径）——不要勉强用，照常按 §2.1–§2.3 自己生成。**不切题的图比没图更糟**。
3. **找缺口**：上两步覆盖完之后，剩下的视觉需求才是新生成的目标。封面没有合适素材就单独生成；正文已经有 2 张用户图就别再凑生成图（总数仍受 §2.4"≤3 张"上限约束）。
4. **位置原则——贴着论点放**：每张图（用户图 + 生成图）必须紧跟它支撑的那段正文。讲到 X 的那段后面就放 X 的图，配 `![图注：...](xxx.png)` + 正文里一句话呼应（如"如图所示，..."）。**禁止把所有图堆到文末当装饰**。

⚠ **用户图同样需要图注 + 正文呼应**：原样塞进文末、不解释、不引用，约等于没用。等价于 §2.5"渲染后必查"——图注说清画的是什么、正文里有一句话呼应到。
⚠ **隐私 / 合规预检**：截图里出现 token / API key / 第三方姓名 / 内部路径 / 真人面孔时，先打码或裁切再用，否则发布等于公开了用户的东西。

#### 2.1 数量与命名
- **必出 1 张封面**：`cover.png`。
- **建议 1–2 张正文图**（最多 3），文件名要**语义化**——能从名字看出画的是什么。
  - ✓ `harness-vs-runtime.png`、`agent-loop-anatomy.png`、`bench-radar.png`
  - ✗ `illustration_1.png`、`illustration_2.png`（除非你真的想不到名字了）
- 图片放进 Payload 目录（如 `articles/<文章标题>/`）。源码（`.mmd` / `.puml`）也一并保留，便于回溯。

#### 2.2 工具选择

| 配图类型 | 推荐工具 | 理由 |
|---|---|---|
| 角色 / 场景 / 概念封面 | `generate_image` 等 AI 绘图 | 视觉冲击、可拟人化 |
| 流程图 / 架构图 / 状态机视觉版 / 序列图 | `mmdc` (官方 `@mermaid-js/mermaid-cli`) | Dagre 边路由稳定、中文字体走 Chromium 原生渲染、`subgraph` + `direction TB` 都能正确解释 |
| 思维导图 / 分类树 / 多分支层级 / 标题封面 | `plantuml.jar` (`@startmindmap`) | 中心放射布局成熟，配 `<style>` 块可做封面 |
| 时序图 / 状态机 / 类图 / 含双向边和多 package 的架构 | `plantuml.jar` (`component diagram`) | DSL 完整性最高，多 package 嵌套和反向边比 Mermaid 表达更清晰 |
| 饼图 / 条形 / 工作量分布 / 数据可视化 | **Python `matplotlib`** | 主题色、尺寸、字体全可控（参考 `articles/Cowork还是ClaudeCode当指挥官/workload-distribution.py`） |
| 雷达图 / 对比表 / 复杂数据图 | `generate_image` 或手绘 SVG | DSL 难以表达 |

> ℹ **为什么是官方 mmdc 而不是 Rust 派生的 mmdr**：曾经把 mmdr 0.2.x 列为首选（吹点：纯 Rust、180ms、无浏览器），但实战踩坑多——多分支树边路由出现错位/断线、`subgraph` 内 `direction TB` 不稳、非 `graph` DSL（pie 等）主题色和 `-w/-H` 参数全部失效。mmdc 用 Puppeteer 调真实 Chromium 跑官方 Mermaid，慢点但所有 DSL、所有主题、所有字体都和 `mermaid.live` 一模一样。仍然偏好启动速度的场景才考虑 mmdr，**默认就是 mmdc**。

#### 2.3 渲染命令（写进脚本的硬性下限）

**Mermaid → mmdc（首选 Mermaid 路径）**
```bash
~/bin/mmdc -i x.mmd -o x.png -e png \
  -w 1800 -H 1200 \
  -s 2 \
  -b white
```
- `-s/--scale 2`：把 Puppeteer 视口放大 2x，最终 PNG 在 1500–2400px 宽度区间，缩放后清晰。复杂图可以提到 `-s 2.5` 或 `-s 3`。
- `-w/-H` 是 viewport 提示，不是强制尺寸——mmdc 会根据内容自适应裁切。需要严格控制比例时，改 `.mmd` 内容（增减节点 / 调 `direction TD/LR`）。
- 中文字体：mmdc 走真实 Chromium 渲染，PingFang SC / Heiti SC 等系统字体直接生效，**不需要** 显式声明。
- 默认背景透明，公众号正文里可能不可读 → 用 `-b white` 显式给白底。
- 首次启动会下载 Chromium（~200MB），之后冷启动 1-3 秒。批量出图用 `-i input.md` 把多张图打包成一个 Markdown 一次性渲染，省启动开销。
- **`sequenceDiagram` 默认会在底部把所有 actor 再画一遍**（mirrorActors），actor 多时会让图变得很高、底部一排重复方块还很碍眼。`.mmd` 首行加 `%%{init: {'sequence': {'mirrorActors': false}}}%%` 关掉，只保留顶部 actor。

**PlantUML → SVG → 高分辨率 PNG（推荐路径）**
```bash
java -jar ~/bin/plantuml.jar -tsvg x.puml                                  # 先出 SVG
rsvg-convert -w 1600 --background-color=white x.svg -o x.png               # 再栅格化到 ≥1600 宽
```
- **不要直接 `-tpng`**：mindmap 等子语法不响应 `-Sdpi`，PNG 会停在 ~700px，正文一缩就糊。SVG → rsvg-convert 这条路对所有 PlantUML 子语法都适用，且自由控制目标宽度。
- **`--background-color=white` 不能省**：PlantUML SVG 默认透明背景，rsvg-convert 默认 `none` 会渲染成透明 PNG，封面在公众号上变成"黑底"或"花底"。中性背景明确指定为 `white` 最稳。
- 目标宽度：插图 **≥1600**，封面 **≥1800**（公众号正文容器约 700px，2-3x 才能保证清晰）。
- 缺 `rsvg-convert` 时安装：`brew install librsvg`。
- `.puml` 顶部三条样板必加，缺一不可：
  ```
  !pragma layout smetana
  skinparam DefaultFontName "PingFang SC"
  skinparam shadowing false
  ```
- 主题二选一开起来：`!theme cerulean-outline`（线框，适合插图）或 `!theme plain`（极简）。
- mindmap 作封面再附 `<style>` 块定制圆角、配色（参考 `articles/Mermaid与PlantUML本地离线渲染方案/cover.puml`）。
- **`package` / `frame` 容器在中英混排标题里用 `packageStyle node`，不要用默认 `rectangle`**：rectangle 风格会在标题位置"挖凹槽"，PlantUML 计算凹槽宽度时假定是英文字符宽度，CJK 字符会被外框横线穿过、看起来像字叠字。`packageStyle node` 把标题画在框内顶部、无凹槽，规避这个 bug。
- **`component diagram` 用作架构 / 流程图**（参考 `articles/Cowork还是ClaudeCode当指挥官/nested-architecture.puml`）：含双向边、多 package 嵌套时，PlantUML component 比 Mermaid `subgraph` 表达更直观、布局更稳定。

**Python matplotlib → 数据图 / 饼图 / 条形 / 排版式封面**
```bash
python3 your_chart.py     # 直接出 PNG
```
- **字体 fallback 链**（macOS 实测顺序）：
  ```python
  mpl.rcParams["font.sans-serif"] = [
      "Hiragino Sans GB",   # macOS 自带，matplotlib 默认能识别 ★
      "Heiti TC", "Songti SC",
      "PingFang SC",        # 不一定在 matplotlib 字体缓存里，作为后备
      "Arial Unicode MS",
  ]
  mpl.rcParams["axes.unicode_minus"] = False
  ```
  > 不要把 `PingFang SC` 放在第一位——它在系统字体里，但 matplotlib 的 fontManager 经常**没扫描进缓存**（Python 3.12+/3.14 上常见），第一位就成了缺失警告。把 `Hiragino Sans GB` 顶在前面是因为 macOS 默认装、matplotlib 默认能找到。
- **中文 weight 最高用 `bold`，不要用 `black`**：Hiragino Sans GB / Heiti TC 没有 black weight，写 `weight="black"` 会渲染成方块字（豆腐）。需要更粗的视觉效果就把 `fontsize` 调大。
- **特殊字符注意**：`✕`(U+2715) 等"绘图记号"在 Hiragino Sans GB 缺字，会触发 `Glyph missing` 警告并显示豆腐；改用 `×`(U+00D7) 通常都有。
- 颜色：用语义化色板（暖=Cowork、冷=Claude Code、灰=其它），不要默认 tab10。
- 尺寸：`figsize=(12, 8), dpi=150` → 1800px 宽，配 `bbox_inches="tight"` 自动裁白边。封面要 4700×2000，用 `figsize=(23.5, 10), dpi=200` + `facecolor` 设置底色。
- **副标题**用 `\n` 拼到主标题下面，而不是 `fig.text(0.5, 0.04, ...)`——后者容易和饼图边缘标签撞。
- **没有 `letterspacing` 参数**：matplotlib 的 `text()` 不支持字间距，要"宽松"效果就在源串里手工插空格（如 `"R E A D I N G"`）。
- 模板可参考 `articles/Cowork还是ClaudeCode当指挥官/workload-distribution.py`。

**封面专用：letterbox 到 16:9 或 1:1（多平台通用比例）**
```bash
# 工具固定路径（随 skill 一起分发）：~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py

# 16:9（横向流程图 / 对比图 / 时间线 —— 默认推荐）
python3 ~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py \
    path/to/cover-raw.png -o cover.png --ratio 1.778 --width 1920 --bg white

# 1:1（视觉冲击型 / 文字海报 / 中心放射构图 —— 兼容微信次条最稳）
python3 ~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py \
    path/to/cover-raw.png -o cover.png --ratio 1 --width 1500 --bg white
```
- **不要再强制 2.35:1**。微信公众号一次推送里头条≈16:9、次条 1:1，掘金 / CSDN 也不吃 2.35:1。三家平台都会按各自规范自动截取——封面给 16:9 或 1:1，平台能裁出合适缩略图。
- 选哪一个：横向内容（`flowchart LR`、`component diagram`、`@startwbs`、对比表）→ **16:9**；中心放射 / 海报式（mindmap、概念图、文字主标题）→ **1:1**。
- `--bg` 选 `white`（默认，最稳，配合公众号正文白底）/ `black`（配合深色封面避免突兀白边）/ `auto`（取源图四角中位色，DSL 渲染图通常和源图主背景一致）/ `#RRGGBB`（精确指定）。
- `-o/--output` 是 `--dst` 的 alias；不传则覆盖源文件，**强烈建议显式传 `-o cover.png` 留底**，把原图保留为 `cover-raw.png`。
- 任意工具（mmdc / PlantUML / matplotlib / AI 绘图）出来的封面，**最后一步**都跑一次 letterbox。原图等比缩放后居中贴到画布上，不裁不拉伸。
- 设计 `.mmd` / `.puml` 时让内容**自然填满目标比例**：4 个横向节点 + 单行文字默认会出 6:1 极扁条，letterbox 到 16:9 后上下白边巨大；改成 3 行多行节点（标题+说明+示例），高度自然增加，白边压到 ≤ 15%。
- 上一版规则错误："封面必须严格 2.35:1"——那是只针对微信公众号头条的旧规则，已废弃。

#### 2.4 构图守则（"看起来不协调"的根因 → 提前规避）

1. **横纵比窗口**：
   - **正文插图**：横向 `1:1 ~ 16:9`，或竖向 `1:1 ~ 3:4`。绝不出现接近 `1:3` 的细长条。
   - **封面 `cover.png`**：默认 **16:9**（横向流程 / 对比 / 时间线），或 **1:1**（视觉海报 / 概念图 / 中心放射）。多平台通用，系统会按各自规范自动截取。最终交付前走 `python3 ~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py <src> -o cover.png --ratio 1.778 --width 1920 --bg white`（16:9）或 `--ratio 1 --width 1500`（1:1）。
   - 白边占比目标 ≤ 15%。原图过扁（如 4 节点 LR ≈ 6:1）→ letterbox 到 16:9 上下白边过大，改 DSL 让节点变高（多行文字、密度更高）。原图过方（mindmap ≈ 1:1）→ 直接选 1:1 比例的 letterbox，或换横向语义结构（如 `@startwbs`）重画再走 16:9。
   - Mermaid / PlantUML 渲染完用 `Read` 看缩略图，不达标就改 DSL 重渲。
2. **节点数控制**：单图节点（不含 subgraph）≤ 12。超出就拆图，或改用表格 / 雷达图。
3. **subgraph 的代价**：Mermaid 多个 subgraph 在 `graph TD` 下默认纵向堆叠，**会把图拉成长条**。两条对策：
   - 合并语义相近的 subgraph，控制在 ≤ 4 个。
   - 切换到 `graph LR` + 强制 `--preferredAspectRatio 4:3`。
4. **配色限定**：单图色相 ≤ 4 类，用 `classDef` 命名后批量应用，禁止逐节点 inline `style`。语义化建议色板：
   - 在线 / 公网（黄）`#FDE68A` / `#D97706` / `#78350F`
   - 离线 / 自托管（绿）`#BBF7D0` / `#16A34A` / `#14532D`
   - 高速 / Rust（红）`#FECACA` / `#DC2626` / `#7F1D1D`
   - JVM / Java（蓝）`#BFDBFE` / `#2563EB` / `#1E3A8A`
5. **字号与中文**：
   - Mermaid 在 1600 宽度下默认字号合适，**不要** 手动调小。
   - PlantUML 必须显式 `DefaultFontName "PingFang SC"`，否则中文走 SansSerif，发糊。
6. **封面密度**：作为缩略图被压缩到 200px 仍要可读 → 中心节点字号 ≥ 22pt，叶子节点 ≥ 14pt，全图主体文字总数控制在 ~30 个汉字以内。

#### 2.5 渲染后必查（不要跳过）

用 `Read` 工具打开生成的 PNG（多模态预览），逐项确认：
- ① 文字未溢出节点框、未截断；
- ② 没有节点 / 边重叠；
- ③ 每条边的箭头方向、起止位置正确（mmdc 走 Dagre 通常没问题；PlantUML component diagram 偶尔会有反向布局，配合 `direction` 与 `-up->` / `-down->` 修正）；
- ④ 长宽比落在 2.4 节守则；**`cover.png` 走 16:9（≈1.778）或 1:1**（用 `python3 -c "from PIL import Image; im=Image.open('cover.png'); print(im.size, round(im.size[0]/im.size[1], 3))"` 验）；不达标先 `mv cover.png cover-raw.png` 备份，再跑 `python3 ~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py cover-raw.png -o cover.png --ratio 1.778 --width 1920 --bg white`（或 `--ratio 1 --width 1500`）修正；
- ⑤ 中文显示清晰：mmdc 用 Chromium 系统字体，正常即可；PlantUML **必须**显式 `skinparam DefaultFontName "PingFang SC"`；
- ⑥ 缩到 30% 仍可读（封面专用）。
任一条不达标，**改 DSL / 换工具 / 调参数后重渲**，不要将就。Mermaid 用 mmdc 还是糊？检查 `-s` 是不是太低、`.mmd` 节点是不是过多。

---

### 阶段 3：起草 Markdown（按文章类型选骨架）

在 Payload 目录下创建 `article.md`。Front matter **格式固定**，正文骨架**按阶段 1 选定的文章类型**走对应模板。

#### Front Matter（固定）

```markdown
---
title: "[有张力、不平铺直叙的标题]"
author: "Agent"
desc: "[60–120 字符摘要，凝练主张与反直觉点]"
collection: "AI"   # 仅限 "AI" 或 "Agent"
cover: "cover.png" # 必填且固定
---
```

> ⚠️ **不要**写 `illustration:` 字段——那是已废弃的旧字段，新文章只用正文 inline `![]()` 引用图片。

#### 正文骨架（按阶段 1 类型六选一）

下面给出 6 种文章类型对应的小标题模板。**只挑一种**，把方括号占位替换为实际内容。

**类型 1：现象解读 / 新闻评论**
```markdown
[钩子段：用一句具体事实 + 一个出乎意料的提问开篇，避免「我们不禁要思考」]

### 事实切片：发生了什么
[把事件压缩到 100 字内，列出谁、何时、做了什么。带出处或链接。]

### 我们怎么看
[亮出主张。给至少一条证据：数据 / 代码 / 案例。]

### 它意味着什么
[谈影响。说清这件事改变了哪些既有结论。]

![架构图：xxx](harness-vs-runtime.png)
```

**类型 2：技术解析 / 概念科普**
```markdown
[钩子段：抛一个开发者每天都遇到但没意识到的具体场景]

### 一个反直觉的类比
[用读者熟悉的事物类比新概念，类比要贴近开发者经验，不要用"巨轮"这种空泛比喻。]

![类比图：xxx](concept-analogy.png)

### 拆开看：它到底怎么工作
[逐层拆解。带代码 / 命令 / 配置片段。]

### 它不解决什么
[列出边界。说清这个方案在哪些场景下不适用。]
```

**类型 3：产品 / 项目对比**
```markdown
[钩子段：明确"在 X 场景下选什么"这个问题]

### 场景与维度
[列出对比维度。建议用表格。]

| 维度 | A | B | C |
|------|---|---|---|
| ... | ... | ... | ... |

![对比雷达图：xxx](bench-radar.png)

### 各自的最佳生态位
[谁适合谁。配上具体团队 / 项目作为例证。]

### 推荐路径
[给一条可执行建议，避免"按需选择"这种废话。]
```

**类型 4：经验沉淀 / 踩坑**
```markdown
[钩子段：直接亮翻车结果，让读者想看你怎么爬出来的]

### 一开始的方案
[说清原始方案与动机。]

### 翻车现场
[贴报错 / 现象 / 数据。这一节必须有真实输出。]

### 真正的根因
[说清为什么会翻。给定位过程。]

### 修正后的做法
[给最终方案。代码 / 命令 / 配置必须可复制。]

![修正前后对比图：xxx](before-after.png)
```

**类型 5：观点檄文 / 立场**
```markdown
[钩子段：直接抛主张。不要绕弯。]

### 反方先讲清楚
[替反方把最强论据说一遍。这一节决定了文章是否有信服力。]

### 我们的论据
[逐条拆。每条配证据：数据 / 案例 / 引用。]

![立场示意图：xxx](position-map.png)

### 重申与边界
[再说一次主张，并说明它在哪些情况下不成立。避免说成放之四海而皆准。]
```

**类型 6：书评 / 读书笔记**
```markdown
[钩子段：用一个具体场景或数据指出"为什么现在重读这本书"，避免"最近读了 XX 这本好书"的开场。]

### 这本书在说什么
[用 200 字内复述全书最核心的一两个论点。带一两条原文引用（注明章节 / 页码 / 作者推特日期）。
这一节决定读者要不要继续看下去——复述要忠实，不要夹私货。]

![核心概念示意图：xxx](concept-diagram.png)

### 我同意的部分
[列 1–3 个让你最受启发的点。每个点：① 作者怎么说 ② 我为什么觉得对 ③ 一个能验证它的具体例子。]

### 我不同意 / 想补充的部分
[列 1–2 个。这一节是书评是否独立思考的试金石。如果完全没有不同意见，要么再读一遍，要么承认这是「推荐文」而不是书评。]

### 它适合谁，不适合谁
[谁读完会有收获，谁读完会觉得没意思 / 被冒犯。直接说，不要"见仁见智"。]
```

---

### 阶段 4：发布前自审 (Pre-flight)

**写完 Markdown 还不能立即发**。先在回复中输出以下检查并逐条过：

```text
【发布前 Pre-flight】
1. 第一句话能让人停止滚动吗？读一遍，如果像"近期，开发者社区迎来了一个重磅消息"——重写。
2. 全文搜陈词滥调（见下方「AI 腔急救包」），命中即改写。
3. 每张配图是否在正文中被引用并解释？孤儿图删掉或补正文。
4. 每个 ### 段落里是否至少有一处具体证据（代码 / 数字 / 案例 / 引用）？没有就补，或砍掉这段。
5. desc 实际长度（中文字符 + 英文字母都算 1）：用 `python3 -c "import sys; s=open('article.md').read(); ... print(len(desc))"` 或简单数一下，确保落在 60–120。
```

#### AI 腔急救包（高危陈词，写出即重写）

| ✗ 写出即重写 | ✓ 替换方向 |
|------|------|
| "我们不禁要思考" / "值得我们深思" | 直接抛具体问题或数据 |
| "标志着 X 进入了一个全新的阶段" | 说清具体改变了什么旧结论 |
| "必将迎来更令人惊叹的进化" / "在 X 滋养下成长为更伟大的产品" | 删掉，或换成可证伪的预测 |
| "在这样的多重夹击下" / "巨头纷纷下场" | 列出具体三家公司及他们做了什么 |
| "无疑会对 X 产生积极的促进作用" | 删掉，或具体说"让 Y 在 Z 场景省 N 倍工作量" |
| "Y 已经走向成熟" 后面不接证据 | 删掉，或后接一个版本号 / 案例 |
| 段落收尾："未来可期 / 拭目以待 / 让我们一同见证" | 直接结束。中文写作不需要总结的总结 |
| 抽象比喻（"如同一艘巨轮""势不可挡的浪潮"） | 换成开发者经验的类比（"像 git rebase 时的 conflict marker"） |

---

### 阶段 5：执行发布

```bash
uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./articles/<文章标题目录>
```

**监控**：
- 看输出有无 `WARNING`，特别是 desc 长度。
- **看到 `通过 AppleScript 执行 JavaScript 的功能已关闭`**：说明 Prerequisites #1 没满足。让用户去 Chrome 菜单栏开开关，重跑即可。
- **看到 `WeChat Official Account tab not found`**：用户没登录公众号后台。让用户在 Chrome 里登录一次。
- **`Cover Setup` / `Reward Setup` / `Collection Setup` 出现 `Failed to complete within N steps`**：是常态，**正文 + 图片注入通常已经成功**。微信编辑器的弹窗 / 下拉对自动化不够友好，超时不影响主体内容。

**收尾必须给用户一份清单**（即使日志里没有明确的 success summary）：

```
✓ / ✗ 标题
✓ / ✗ 正文（看 "Filled via paste event"）
✓ / ✗ N 张图片（看 "Successfully initiated image paste/upload" 出现次数）
✓ / ✗ 原创声明（看 "Originality badge found"）
✗ 封面 → 让用户在编辑器右侧点「从正文选择」
✗ 合集 → 手动选
✗ 保存为草稿 → 手动点
```

把还需手动补的步骤明确告诉用户，比"已发送"更负责。

## Example Usage

**用户输入**：
```text
帮我写一篇关于 Claude Code 的护城河的文章，发到微信草稿。
```

**Agent 执行**：
1. 输出【内容质量自检】+【形式自检】。例如主张定为「Claude Code 的护城河不是模型，而是 Anthropic 把 Agent 内化进了模型训练目标」，文章类型选「观点檄文」。
2. 生成 `cover.png` + `harness-internalized.png`，存到 `articles/Claude_Code的护城河/`。
3. 按"观点檄文"骨架写 `article.md`：先抛主张，再讲反方，再给三条证据（含具体版本号或引用），收尾不写"未来可期"。
4. 输出【发布前 Pre-flight】，确认开头不是"近期…"、所有 ### 段落都有证据、图片都在文中引用、desc 长度合规。
5. 跑 `uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./articles/Claude_Code的护城河`。
6. 向用户报告草稿已保存，提醒手机预览。

## Common Mistakes

- **跳过阶段 1 直接写正文**：产出会回到三段式套路。如果你"知道怎么写"也要走一遍——主要是为了把主张和证据落地到文字。
- **CoT 只答形式不答主张**：阶段 1A 是核心。如果"一句话主张"答不出陈述句，文章一定是空的。
- **front matter 写 `illustration:` 字段**：已废弃，写了也不读。配图统一用正文 inline `![]()`。
- **图片用 `illustration_1.png` 这类无语义文件名**：会让你忘记图到底在画什么，最后变成孤儿图。
- **图片写成 `![[图注：…]](xx.png)`（双层方括号）**：是 Markdown 语法异常，部分渲染器渲染不出。标准写法是 `![图注：…](xx.png)`。
- **图片文件名带时间戳**（AI 绘图工具常见输出）：必须重命名去时间戳，否则正文引用对不上。
- **忽略用户在对话里附的图片，自己从零生成全套配图**：用户的截图 / 产品图 / 手稿往往是最强一手证据，比 AI 重画更可信。先按 §2.0 盘点，再决定要不要补图——"我画一张更整齐"是高频误判。
- **把用户图都堆在文末当装饰**：用户给了 3 张图、正文一处没引用、整堆放在结尾——读者读不到上下文，等于没用。每张图必须贴着它支撑的那段正文（§2.0 位置原则），并配图注 + 一句话呼应。
- **用户图直接用 `IMG_2024.png` / `Screenshot_20260508.png` 之类原始文件名**：和 AI 时间戳文件名同一种坑，正文引用对不上、复盘也不知道哪张画的是什么。一律按 §2.1 语义化重命名（如 `claude-code-task-list.png`）再用。
- **desc 写成 200+ 字符**：parser 只警告不阻断，但微信编辑器会截断。严格 60–120。
- **collection 写成 "AI/Agent" 之外**：parser 默认走 "AI"，但发布行为可能和你预期不一致。仅限两个值。
- **正文小标题原封不动用 `### 1. 核心痛点与背景`**：那是旧模板的化石。按阶段 3 选定的类型走对应骨架。
- **图表细长得像传真纸**：Mermaid 多个 subgraph 默认 TD 堆叠，长宽比直奔 1:3。把 `flowchart TD` 改成 `flowchart LR`、把 subgraph 数量压到 ≤ 4，必要时拆图。
- **用 Mermaid 画 pie / bar / 数据分布**：Mermaid 的 pie 子语法只能拿到默认配色和小尺寸，无法适配文章风格。饼图 / 条形 / 数据图直接走 Python matplotlib（参考 `articles/Cowork还是ClaudeCode当指挥官/workload-distribution.py`）。
- **mmdc 把 `.mmd` 渲成 SVG 后用 rsvg-convert 转 PNG，结果中文全没了**：Chromium 渲染 SVG 时把字体当外部资源，rsvg-convert 转 PNG 时找不到。直接 `mmdc -i x.mmd -o x.png -e png -s 2`，PNG 由 Chromium 直接栅格化字体，不要走 SVG 中转。
- **Mermaid `sequenceDiagram` 底部一排 actor 重复方块**：mirrorActors 默认开。actor ≥4 时尤其碍眼、还把图拉高。`.mmd` 首行加 `%%{init: {'sequence': {'mirrorActors': false}}}%%`，只保留顶部 actor 即可。
- **PlantUML `package` 标题里中文被横线穿过、字叠字**：是 `packageStyle rectangle` 在 CJK 标题处"挖凹槽"宽度算错，外框横线穿过字符。改 `skinparam packageStyle node`，标题改画在框内顶部，无凹槽。
- **PlantUML 直接 `-tpng` 出图**：mindmap 子语法不响应 `-Sdpi`，输出停在 ~700px 宽，正文里发糊。改走 `-tsvg` + `rsvg-convert -w 1600`。
- **PlantUML 没设字体直接画中文**：默认走 SansSerif，渲染像马赛克。`skinparam DefaultFontName "PingFang SC"` 必加。
- **`cover.png` 比例选错或被压扁**：默认 16:9，海报型 1:1。**不要再强制 2.35:1**——那是只针对微信公众号头条的旧规则，次条走 1:1，掘金 / CSDN 都按自己规范裁切。最后一步统一走 `python3 ~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py <src> -o cover.png --ratio 1.778 --width 1920 --bg white`（横向）或 `--ratio 1 --width 1500`（方形）。原图过扁（如 4 节点单行 LR ≈ 6:1）letterbox 后上下白边巨大 → 改 DSL 让节点变高（多行文字 / 增加密度），不要靠 letterbox 蒙混。
- **不看渲染结果就引用进文章**：阶段 2.5 的"渲染后必查"六项不能跳。
- **Mermaid 写 `-.x.->` / `-.x.->` 想要"被划掉的虚线箭头"**：Mermaid **没有这种语法**，parser 直接抛 InputError，整张图渲染失败。要表达"此路不通"用 `-. 标签 .-> ` 配合中文标签（`-. 此路不通 .->` / `-. 不可行 .->`），或者画两类节点用 `classDef` 区分颜色。
- **matplotlib 中文字体设成 `["PingFang SC", ...]` 第一位**：在 Python 3.12+/3.14 上 matplotlib 的 fontManager 经常没把 PingFang SC 扫进缓存，第一位就是缺失警告。改用 `["Hiragino Sans GB", "Heiti TC", "Songti SC", "PingFang SC", ...]`，把 macOS 自带且 mpl 默认能识别的 `Hiragino Sans GB` 顶在前面。
- **matplotlib 用 `weight="black"` 渲染中文**：Hiragino Sans GB / Heiti TC 没有 black 字重，会渲染成方块字（"豆腐"）。中文最高用 `weight="bold"`，要更醒目就调 `fontsize`。
- **PlantUML SVG → PNG 漏了 `--background-color=white`**：PlantUML SVG 默认透明，rsvg-convert 默认 `none`，PNG 在某些查看器里看着白底其实是透明，公众号背景一变就花掉。`rsvg-convert --background-color=white` 必加。
- **`fit_wechat_cover.py` 路径写成相对路径 `tools/fit_wechat_cover.py`**：CWD 不对就 ENOENT。固定路径是 `~/.claude/skills/blogger-agent/tools/fit_wechat_cover.py`，永远写绝对路径。
- **`fit_wechat_cover.py` 不传 `-o`，源文件被覆盖**：默认 `--dst` 等于 `--src`，调用一次原图就被替换掉了。**始终显式传 `-o cover.png` 留底**，把原图保留为 `cover-raw.png`。
- **微信发布 stage 中途超时就放弃汇报**：UI state machine 三五个 stage 超时是常态（封面 / 合集 / 赞赏 / 草稿按钮），但**正文和图片已经注入**。一定要给用户一份"哪些成功 / 哪些要手动补"的最终清单（见阶段 5），不要扔下一句"发布失败"就跑。

## 附录：本地渲染工具一次性安装

只在本地未安装时才需要执行，安装一次终身受益。仓库根目录 `README.md` 也有同款指引（面向工具使用者）；这里是面向 Agent 的可执行版本。

```bash
mkdir -p ~/bin

# 1. mmdc (Mermaid 官方 CLI，Puppeteer + Chromium，跟 mermaid.live 一致)
#    若 npm 全局目录是 root 所有，先把 prefix / cache 切到家目录，避开 sudo
npm config set prefix '~/.npm-global'
npm config set cache '~/.npm-cache'
npm install -g @mermaid-js/mermaid-cli           # 自动下载 Chromium ~200MB
ln -sf ~/.npm-global/bin/mmdc ~/bin/mmdc

# 2. plantuml.jar (最新版)
curl -sSL -o ~/bin/plantuml.jar 'https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar'

# 3. librsvg（PlantUML SVG → PNG 必备）
brew install librsvg

# 4. 验证
~/bin/mmdc --version          # 期望 11.x
java -jar ~/bin/plantuml.jar -version | head -1
rsvg-convert --version
```

依赖：
- `node` ≥ 18.19（`brew install node`）—— mmdc 必备
- `java`（macOS 自带或 `brew install openjdk`）—— PlantUML 必备
- `python3` + `matplotlib`（`pip install matplotlib`）—— 数据图必备

mmdc 的磁盘占用主要是 Chromium（~200MB）。冷启动 1–3 秒，比纯 Rust 实现慢，但布局质量与 `mermaid.live` 完全一致，**复杂图不会再翻车**。
