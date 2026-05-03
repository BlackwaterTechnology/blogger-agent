# Blogger Skills

## Project Overview

`blogger-agent` is an AI agent automation project. The ultimate vision is to allow a user to provide a topic or viewpoint, from which an AI Agent will automatically generate a complete article and publish it to mainstream blog platforms such as WeChat Official Accounts (微信公众号), Juejin (稀土掘金), and CSDN.

Currently, the project focuses on the core capability of automating the publishing of local Markdown articles to WeChat Official Accounts. It has been refactored into a standard, extensible Python package with built-in MCP (Model Context Protocol) support for modern AI agent integrations.

## Architecture

This tool uses Python and AppleScript (via `ChromeDomController` and `rookiepy`) to interact with a running instance of Google Chrome on macOS. It parses Markdown files and uses browser automation to inject the content into the web editor.

It offers two primary interfaces for Agents:
1. **MCP Server (`mcp_server.py`)**: Exposes structured JSON-RPC tools (`publish_article`) for modern IDEs like Claude Code, Cursor, and Codex.
2. **CLI Agent Skill (`cli.py`)**: Provides traditional terminal execution paths (via `uvx` and `SKILL.md`) for Bash-driven agents.

## Directory Structure

*   **`src/blogger/`**: The core Python package.
    *   **`cli.py`**: The CLI entry point for terminal execution (`blogger --payload ...`).
    *   **`mcp_server.py`**: The FastMCP server exposing tools for Claude Code and Cursor.
    *   **`core/`**: Core utilities including `chrome.py` (browser automation) and `markdown_parser.py`.
    *   **`platforms/`**: Platform-specific publisher state machines (e.g., `wechat.py`).
*   **`pyproject.toml`**: Standard Python packaging and dependency management.
*   **`Makefile`**: Standard orchestration for development tasks (`make install`, etc.).
*   **`skills/blogger-agent/SKILL.md`**: The traditional Agent Skill definition (2026 Open Agent Skills compatible).
*   **`articles/test_data/`**: Directory containing sample markdown articles and assets for testing the publishing flow.

## Usage

### 1. Zero-Install Integration (For Agents)

**MCP (Claude Code, Gemini CLI, Codex):**
```bash
claude mcp add blogger-agent uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger-mcp
```

**Skill (Traditional Bash Agents):**
```bash
uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger --payload ./payload_dir
```

### 2. Manual Local Development

```bash
# Setup
make install

# Run Publisher manually
blogger --payload articles/test_data/
```

## Development Context & Guidelines

*   **Extensibility**: When adding new platforms (like Juejin or CSDN), create a new class in `src/blogger/platforms/` that conforms to the publisher pattern, and register it in the CLI parser and MCP tool definitions.
*   **No Framework Overhead**: Keep dependencies minimal. Ensure that any newly added logic is abstracted cleanly from the `WechatPublisher` state machine.

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
| **缩短延迟** | `keystroke "Agent"` → `delay 0.05` → Enter | AppleScript `keystroke` 是逐字符发送的，0.05s 时文字可能还没打完，导致标签错位 |
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

1. **绝不在 AppleScript 操作间插入 JS 调用**：`execute_javascript`（通过 JXA/osascript）会导致 Chrome 的 input 失去焦点。打字和 Enter 必须在同一个 AppleScript 调用中。
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
