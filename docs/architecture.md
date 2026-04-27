# Blogger-Agent 技术架构文档

## 1. 鼠标点击功能实现原理解析

针对“鼠标点击功能是否由 AppleScript 实现”的疑问，答案是：**页面内元素的鼠标点击不是由 AppleScript 原生点击实现的，而是通过注入 JavaScript 模拟 DOM 事件实现的。**

本项目在浏览器自动化层面采用了**分层架构**：

- **AppleScript (OS 级别操作)**: 主要负责操作 Chrome 浏览器的原生窗口。例如：遍历并寻找特定的标签页、切换标签页前置、读取标签页 URL，以及触发系统级的键盘快捷键（如 `Cmd + V` 粘贴剪贴板图片、`Cmd + X` 剪切）。
- **JavaScript 注入 (DOM 级别操作)**: 对于网页内部的具体操作（如点击“选择封面”按钮、勾选“原创”协议、处理 React 拦截的点击事件等），是由 Python 组装一段具有特定逻辑的 JavaScript 代码，然后通过 AppleScript 的 `execute tab ... javascript ...` 命令，将该 JS 代码注入到 Chrome 页面中执行。
  - **点击实现细节**: 在 `wechat.py` 中，你可以看到 `clickReactElement(el)` 这样的 JS 函数。它会首先尝试查找 React 内部的 `__reactEventHandlers$` 属性以直接触发绑定的 `onClick` 方法，如果找不到，则通过 `el.click()` 或 `new MouseEvent('click', ...)` 模拟原生鼠标事件。这种方式比 AppleScript 原生点击坐标要稳定得多，不受屏幕分辨率和页面滚动位置的影响。

---

## 2. 整体项目技术架构

`blogger-agent` 的定位是一个将 Markdown 自动发布到主流博客平台的 AI Agent 自动化项目。为了同时兼容传统的命令行 Agent 和现代的 IDE Agent，项目采用了标准化的结构设计。

### 2.1 核心层 (Core Layer)
位于 `src/blogger/core/` 目录，提供底层通用的工具模块：
- **`chrome.py` (ChromeDomController)**: 浏览器的自动化引擎。封装了底层的 `osascript` (AppleScript) 调用，提供了一套面向对象的 API，用于查找标签页、切换窗口、以及向指定的标签页注入执行 JavaScript 代码。
- **`markdown_parser.py`**: Markdown 解析器，负责将本地的 Markdown 文件转换为适合各个平台富文本编辑器接收的 HTML 格式和纯文本。

### 2.2 平台层 (Platform Layer)
位于 `src/blogger/platforms/` 目录，存放各个发布平台的具体业务逻辑：
- **`wechat.py` (WechatPublisher)**: 微信公众号自动化发布状态机。它定义了一系列重度依赖 DOM 操作的自动化步骤：
  1. 寻找或重定向到微信公众号图文编辑页面。
  2. 注入标题、作者、摘要内容。
  3. 通过剪贴板模拟粘贴，将富文本 HTML 灌入 `ProseMirror` 编辑器。
  4. 自动化处理上传配图、选择合集标签、确认原创和赞赏协议。
  5. 最终点击“保存草稿”。

### 2.3 Agent 接口层 (Interface Layer)
为了让各种大模型 Agent 能够轻松调用该能力，项目提供了两种主流的暴露方式：

1. **MCP (Model Context Protocol) 接口** 
   - **`mcp_server.py`**: 基于 FastMCP 构建的服务器。它向 Claude Code、Cursor 等现代 Agent 暴露结构化的 JSON-RPC Tool（如 `publish_article` 工具）。Agent 可以直接传入结构化的 JSON 数据触发发布流程。
   
2. **Open Agent Skills 接口**
   - **`cli.py` & `SKILL.md`**: 为传统的基于 Bash 的 Agent 提供支持。通过标准的 CLI 命令行参数解析（如 `blogger --payload ...`）触发功能，并通过 `SKILL.md` 遵循 2026 Open Agent Skills 规范进行自描述与自动发现。

---

## 3. 架构优势

1. **无头依赖 (Zero-Dependency for Browser)**: 没有使用 Selenium、Puppeteer 等重量级无头浏览器框架，不需要单独配置 ChromeDriver。直接通过 macOS 自带的 AppleScript 接管用户当前正在登录的日常 Chrome 浏览器，天然继承了用户的 Cookie 和登录态。
2. **双端适配**: 核心发布逻辑被高度解耦，既可以通过 MCP 协议作为微服务运行，也可以通过 UVX 作为一次性脚本运行。
3. **基于状态机的容错**: `wechat.py` 中使用了 `run_ui_state_machine`。由于现代前端框架（React/Vue）渲染具有异步延迟，脚本不会一次性死板地执行所有 JS，而是通过状态机轮询页面状态（如等待弹窗渲染完成），极大地提高了自动化的稳定性。
