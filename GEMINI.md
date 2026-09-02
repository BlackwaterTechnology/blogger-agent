# Blogger Skills

## Project Overview

`blogger-agent` is an AI agent automation project. The ultimate vision is to allow a user to provide a topic or viewpoint, from which an AI Agent will automatically generate a complete article and publish it to mainstream blog platforms (WeChat Official Accounts, Juejin, CSDN) and short-video platforms (Bilibili, WeChat Channels).

The project offers core capabilities for:
1. **Article Publishing**: Automating the publishing of local Markdown articles to web-based editors.
2. **Video Generation**: Generating cinematic videos from documents or URLs using Google NotebookLM.
3. **Diagram Generation**: Creating infographics and technical diagrams via Kroki.

## Architecture

This tool uses Python and AppleScript to interact with a running instance of Google Chrome on macOS. It finds the target platform's tab and injects content using a combination of JavaScript execution and simulated keystrokes.

### Key Components
- **Chrome Controllers**: Specialized controllers in `src/blogger/core/` (`cdp_chrome.py`, `jxa_chrome.py`, `chrome.py`) handle different aspects of browser interaction. CDP-based controllers allow for deeper interaction, while JXA handles macOS focus management.
- **Markdown Parser**: `src/blogger/core/markdown_parser.py` uses `python-frontmatter` to parse articles, handling metadata and local image path rewriting.
- **Platform Publishers**: Platform-specific state machines in `src/blogger/platforms/` manage the complex UI flows for each site.
- **Interfaces**:
    1. **MCP Server (`mcp_server.py`)**: Exposes structured JSON-RPC tools for modern IDEs. Note: it uses a round-trip mechanism where it materializes a temp Markdown file for the parser to consume.
    2. **CLI Agent Skill (`cli.py`)**: Provides traditional terminal execution paths.

## Directory Structure

*   **`src/blogger/`**: Core Python package.
    *   **`cli.py`**: CLI entry point and high-level orchestration (handling subcommands like `video`).
    *   **`mcp_server.py`**: FastMCP server for tool-based agents.
    *   **`core/`**:
        *   `cdp_chrome.py` / `jxa_chrome.py` / `chrome.py`: Browser automation core.
        *   `markdown_parser.py`: YAML frontmatter and image processing.
        *   `diagrams.py`: Kroki-based diagram generation.
    *   **`platforms/`**: Publisher implementations.
        *   `wechat.py`, `csdn.py`, `juejin.py`: Blog platforms.
        *   `bilibili.py`, `wechat_video.py`, `wechat_channels.py`: Video platforms.
*   **`skills/`**: Agent skill definitions (`SKILL.md` files) for various capabilities.
*   **`articles/`**: 文章 Payload 目录。所有新建文章目录**必须前置当前日期**，格式为 `YYYY-MM-DD-<slug>`（例如 `2026-08-03-true-nobility`）。
*   **`watermark_remover.py`**: Utility for removing AI-generated watermarks from videos.
*   **`monitor_video.sh`**: Reference script for the background polling workflow.

## Video Generation Workflow (NotebookLM)

Video generation via Google NotebookLM is a long-running process (15–45 minutes). To maintain efficiency and avoid blocking, agents follow a specialized subagent-based workflow.

### 1. Generation
Initiate cinematic video generation:
```bash
notebooklm generate video --format cinematic "Instructions" --json
```

### 2. Background Polling & Download (Subagent Pattern)
Do not wait in the main process. Dispatch a subagent (`@generalist`) to handle the polling and download asynchronously:

- **Phase A (Initial Wait)**: `sleep 600`. (Cinematic videos never finish in under 10 minutes).
- **Phase B (Polling Loop)**: Every 60 seconds, check status using `notebooklm artifact list -n {notebook_id} --json`.
- **Phase C (Completion)**: Once `status` is `completed`, download the video:
  ```bash
  notebooklm download video ./videos/[topic]/video.mp4 -a {artifact_id} -n {notebook_id}
  ```

### 3. Post-Processing
After download, the video typically requires watermark removal:
```bash
python watermark_remover.py ./videos/[topic]/video.mp4 --model lama
```

## Browser Automation Lessons Learned

### CSDN 标签设置 — el-autocomplete 组件自动化

CSDN 的文章标签输入框是 Element UI 的 `el-autocomplete` 组件（placeholder: "请输入文字搜索，Enter键入可添加自定义标签"）。以下是自动化过程中踩过的坑和最终解决方案。

#### 核心问题

`el-autocomplete` 在**每个字符输入后立即搜索**（debounce=300ms），并**自动高亮第一个建议**。按 Enter 时会选中高亮的建议而非添加自定义标签。例如：输入 "Agent" 时，输入 "A" 后 autocomplete 就高亮了 "AI"，Enter 选中了 "AI" 而不是 "Agent"。

#### 失败方案记录

| 方案 | 做法 | 失败原因 |
|---|---|---|
| **Escape 关闭下拉** | 打字 → `key code 53`(Esc) → Enter | Esc 冒泡关闭了父级发布对话框（modal） |
| **JS 隐藏下拉 + 分离 Enter** | AppleScript 打字 → JS `display:none` → AppleScript Enter | `execute_javascript` 通过 JXA 调用会**抢走 Chrome input 焦点**，后续 Enter 打空 |
| **Up 箭头取消高亮** | 打字 → `key code 126`(↑) → Enter | el-autocomplete 的 debounce=0 或极短，打字过程中 autocomplete 已出现并高亮，Up 时机不对 |
| **缩短延迟** | `keystroke "Agent"` → `delay 0.05` | AppleScript `keystroke` 是逐字符发送的，0.05s 时文字可能还没打完，导致标签错位 |
| **纯 JS KeyboardEvent** | JS 设值 + `dispatchEvent(new KeyboardEvent('keydown', {key:'Enter'}))` | Vue 不响应合成的 KeyboardEvent |

#### ✅ 最终方案：剪贴板粘贴

```python
# 1. 复制到系统剪贴板（Python）
subprocess.run(["pbcopy"], input=tag_name.encode(), check=True)

# 2. Cmd+A 全选 → Cmd+V 粘贴 → Enter（AppleScript）
# 粘贴是即时的，50ms 后 Enter 时 autocomplete 还没出现
keystroke "a" using {command down}   # 选中旧文本
delay 0.1
keystroke "v" using {command down}   # 粘贴（瞬间完成）
delay 0.05                           # autocomplete 需要 300ms+，此时还没出现
key code 36                          # Enter → 走"添加自定义标签"路径
```

**为什么有效**：`Cmd+V` 粘贴是一次性写入所有字符（不是逐字符），50ms 后按 Enter 时 autocomplete 的 debounce 定时器还没触发，下拉还没出现，所以 Enter 走的是 input 原生的"添加自定义标签"路径。

#### 通用规则

1. **绝不在 AppleScript 操作间插入 JS 调用**：`execute_javascript`（通过 JXA/osascript）会导致 Chrome 的 input 焦点丢失。打字和 Enter 必须在同一个 AppleScript 调用中。
2. **粘贴优于打字**：对于有 autocomplete/下拉联想的输入框，用 `pbcopy` + `Cmd+V` 代替 `keystroke`，避免逐字符输入触发搜索。
3. **面板关闭用精确按钮**：标签面板的关闭使用 `button.modal__close-button`（X 按钮），不要点击面板外部（可能点到其他控件）或按 Escape（会关闭父 modal）。
4. **先标签后分类**：标签和分类共用 `button.tag__btn-tag` 类名，必须先设置标签并关闭面板后再设置分类，避免 DOM 选择器互相干扰。

### CSDN 分类专栏设置 — 浮动面板 checkbox 自动化

#### 核心问题

分类专栏区域有一个 `button.tag__btn-tag`（文本"新建分类专栏"），容易误以为是"展开现有分类列表"的按钮。实际上它打开的是**新建分类的输入框**（很小的 input），脚本在此 input 中没输入内容就按了 Enter，导致分类设置失败。

#### DOM 结构

```
.form-entry (containing "分类专栏")
  └── .tag__box (h=32px, acts as anchor)
        ├── .tag__item-list — 已选分类显示区
        ├── button.tag__btn-tag "新建分类专栏" — ⚠️ 打开新建输入框，不是展开列表！
        └── .tag__options-content (position:absolute, top:32px, z-index:2)
              └── .tag__option-box × N — 每个现有分类
                    └── input.tag__option-chk (checkbox)
```

关键发现：`.tag__options-content` 是 **`position: absolute`** 的浮动面板，**默认已存在于 DOM 中**（height=198px），不需要任何展开操作。

#### 失败方案

| 方案 | 失败原因 |
|---|---|
| 点击 "新建分类专栏" 按钮展开 | 这个按钮打开的是新建输入框，不是列表 |
| 点击 `.tag__option-box`（外层 div） | Vue 不响应外层 div 的 click 事件，checkbox 状态不变 |

#### ✅ 最终方案：直接 click checkbox input

```javascript
// 必须点击 input.tag__option-chk 本身，不是它的父元素 .tag__option-box
const cb = box.querySelector('input.tag__option-chk');
if (cb && !cb.checked) {
    cb.click();  // 直接 click input 元素，Vue 能正确响应
}
```

#### 通用规则

1. **区分"新建"和"展开"**：`button.tag__btn-tag` 在标签区和分类区含义不同。标签区是"添加文章标签"（打开搜索面板），分类区是"新建分类专栏"（打开新建输入框）。不要假设同类名按钮功能相同。
2. **Click 层级要精确**：Vue/Element UI 的 checkbox 必须直接 click `input` 元素。click 外层 `div`/`label` 可能不触发 Vue 的响应式更新。
3. **浮动面板无需展开**：`position: absolute` 的面板可能已在 DOM 中渲染，只是通过定位浮在父容器外，不需要额外的展开/显示操作。

### 图片生成与渲染质量标准

1. **4 大配图模态矩阵与黄金混配 (Multi-Modal Visual Strategy)**：
   - **模态 1：具象概念隐喻 / 场景插画**：使用 `generate_image`（AI 绘图）在文章开篇或矛盾处生成**具象场景与物理实体隐喻**（如蒸汽机械 vs 折纸天鹅、石壁发光代码），激活右脑好奇心。
   - **模态 2：结构拓扑 / 垂直流水线**：原生 SVG / PlantUML 负责核心机制与端到端时序流（1200px 宽度，字号 ≥28px）。
   - **模态 3：多维决策矩阵 / 二元对抗**：原生 SVG (2x2 网格 / 双栏对抗) 给出技术选型与策略落地。
   - **模态 4：实证量化图表 / 终端切片**：Matplotlib (DPI 300+) 给出收益曲线与基差剪刀差，CLI 终端卡片展示真实命令输出。
   - **黄金混配 SOP**：深度长文推荐采用“感性隐喻 ➔ 严密拓扑 ➔ 决策落地”的节奏编排，**严禁全篇 100% 堆砌单一深蓝框图**。
2. **去除 AI 味的 5 大杂志社论艺术风格 (5 High-Taste Editorial AI Styles)**：
   - 使用 `generate_image` 时，**坚决杜绝 4 大廉价 AI 俗套**（发光蓝脑、机械手握手、科幻全息 HUD、乱码假字）。
   - 统一采用国际顶级社论风格：① 现代杂志社论扁平插画 (Modern Editorial Flat Vector)；② 实体机械/物理隐喻对比 (Physical Mechanical Metaphor)；③ 复古清晰线稿与版画 (Vintage Ligne Claire / Woodcut)；④ 等轴测微缩黏土模型 (Isometric Clay & Diorama)；⑤ 包豪斯几何构成主义 (Bauhaus Constructivism & Swiss Print)。
3. **SVG 多主题色板系统 (Multi-Theme Palette System)**：
   - 支持 4 款主题色板：① `slate_navy`（深曜黑蓝，适合底层系统与量化）；② `swiss_white`（瑞士白底明色，适合商业社论与认知反思）；③ `terracotta_warm`（暖陶米纸，适合职场与教育）；④ `forest_emerald`（深林薄荷，适合工程效能与开源）。
4. **清晰度与画布标准**：
   - **正文 SVG 画布标准**：正文配图推荐采用 **`1200px` 宽度**（如 `viewBox="0 0 1200 800"` 3:2、`1200 900` 4:3、`1200 1000` 纵向流），缩放比达 0.30。封面保持 16:9（`1920 1080` 或 `1200 675`）。
   - **PlantUML / Mermaid 图表引擎**：必须保持 **DPI 300+**（PlantUML 设置 `skinparam dpi 300` 或 `360`，Mermaid 使用 `-s 3` 3x 采样）。
5. **移动端字号硬底线与防拥挤铁律 (CRITICAL)**：
   - **字号绝对底线**：在 1200px 画布中，**全图文字绝对禁止低于 28px**（核心大标题 `44px~52px`，卡片标题 `36px~42px`，正文节点 `32px~36px`，次要说明 `28px~30px`）。若使用 1600px 画布，底线必须提升至 `≥ 36px`。
   - **横向分栏上限（最多 2 栏）**：**严禁横向并排 3 栏或 4 栏小卡片**！多步骤时序流转必须采用**垂直纵向流动（Top-to-Bottom Stacked Pipeline）**或 **2x2 四象限网格**。
   - **卡片极简短语化**：每个节点/卡片严格限制在 2~3 行文字以内（每行 8~14 字），严禁在图内填入整句长句或段落，详细逻辑留给正文。
6. **SVG 高画质转换命令**：`sips` 转换 SVG 为 PNG 时**必须强制包含 `--resampleWidth 1920`** (例如 `sips -s format png --resampleWidth 1920 input.svg --out output.png`)。
7. **Matplotlib**：Python 导出图表必须显式声明 `plt.savefig(..., dpi=300, bbox_inches='tight')`。
8. **文章封面设计与 Hook 解耦规范**：文章封面大标题必须提炼为 **4 ~ 8 字冲突短语/爆破钩子**（如 `11% 的谎言？`），字号保持 `64px~76px`，并采用“左侧 Hook + 右侧微型数据对比/信息图卡片（字号 `28px~34px`）”的双栏复合杂志架构。
9. **原生 SVG 矢量图优先原则 (Native SVG First)**：对于正文中的**交互时序图/序列图、多维度对比卡片矩阵、复杂系统拓扑图**，**强制优先使用原生 SVG 代码配合 `sips -s format png --resampleWidth 1920` 渲染**。消除 PlantUML 默认渲染造成的节点截断与样式僵硬问题。


### 文章 Markdown 文本与符号渲染规范

1. **禁用 LaTeX 箭号数学公式**：在生成面向微信公众号、掘金、CSDN 等平台的 Markdown 文章时，**严禁使用 LaTeX 行内数学公式语法（如 `$\rightarrow$`, `$\Leftarrow$`）表示逻辑方向**。微信公众号等主流编辑器的 Markdown 解析器不会编译行内 LaTeX 数学公式，会导致文章中直接暴露 `\rightarrow` 等原始字符串。
2. **统一使用原生 Unicode 符号**：文章正文中的逻辑连接符必须直接使用标准的原生 Unicode 符号（如 `→`, `←`, `↑`, `↓`, `⇒`, `⇔`），确保在所有移动端与 WEB 编辑器中 100% 正确渲染。
3. **列表块前强制插入空行**：Markdown 语法中，无序列表（`*`, `-`）和有序列表（`1.`, `2.`）上方必须显式留出空行。若没有空行，Markdown 转换引擎（如 Blogger / 微信 / CSDN）会将列表项直接混入前文 `<p>` 段落中，导致发布页面渲染为无换行的平铺文字。
4. **标题排版与 20 字符长度铁律 (Title Typography & Character Ceiling Standard)**：
   - **图片消息 20 字符硬顶 (CRITICAL)**：微信图片消息（小绿书图文，`type: "photo"`）标题输入框设有 **20 字符绝对上限**。标题必须严格控制在 **≤ 20 字符**（推荐 12 ~ 18 字符），严禁超出 20 字导致微信报错或截断。
   - **标点零浪费与空格清零**：严禁在标题中使用带有两侧空格的分隔符（如 ` ｜ `、` | `、` —— `、` - `）。标点统一使用中文全角无空格标点（如中文冒号 `：`、问号 `？`、逗号 `，`、引号 `「」`）。
   - **4 大极简爆款标题范式**：
     - ① 设问冲突型：`[设问短语？][核心定论/真相]`（如 `冥想是空耗时间？大脑正在信息戒断` - 17字）；
     - ② 钩子冒号型：`[爆破词]：[解法/商业本质]`（如 `0.99刀真相：揭秘域名暴利定价` - 15字）；
     - ③ 反直觉警示型：`[警示痛点]，[破局手段]`（如 `别死磕语法：成人英语极简自测法` - 16字）；
     - ④ 单句高张力直击：一句话穿透核心利益点（如 `为什么顶尖AI都在做模型蒸馏` - 14字）。
   - **长文标题可视区前置**：普通长文文章即便上限为 64 字，前 18~22 字也必须具备完整认知钩子，杜绝冗长前缀与空格破折号。
5. **微信图片消息 ProseMirror 换行与段落注入规范 (CRITICAL)**：
   - **核心坑点**：微信图片消息的描述输入框（`.share-text__input .ProseMirror`）底层 Schema 将伴随文案设计为单个段落流，不支持多 `<p>` 块。若将文案按 `\n\n` 拆为多个 `<p>` 注入，ProseMirror 的 DOMParser 会在解析时剥离 `<p>` 标签并平铺合并其子节点，导致**段落间换行全部丢失、小标题与正文粘连**。
   - **黄金方案**：严禁用多 `<p>` 分段。文案必须统一包裹在单一 `<p>` 节点内，并将所有换行符 `\n` 显式转换为 `<br>`（两个连续换行 `\n\n` 转换为 `<br><br>`）。ProseMirror 会将 `<br>` 精确映射为 `hard_break` 节点，完美保留单行换行与段落间空行。
   - **伴随文案排版铁律**：`💡 核心洞察：`、`【模块标题】`、`💬 互动探讨：` 必须各自独占一行且上方保留空行；列表项（`• ` 或 `1. `）必须逐行独立换行，严禁标题与正文首行挤在同一行。


