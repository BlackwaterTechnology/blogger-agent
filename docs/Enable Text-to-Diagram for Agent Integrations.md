# Enable Text-to-Diagram for Agent Integrations

目前类似 Claude Code 或 Gemini CLI 等纯文本界面的 Agent 不支持原生的图片生成（如 Midjourney 或 DALL-E）。为了让这些 Agent 也能生成文章的封面和插图，我们需要一种将纯文本（Mermaid、PlantUML）转换为图片的集成方案。

## 架构选型与策略

为了保持 `blogger-agent` 倡导的**“Zero-dependency (零框架负担)”**，如果在本地安装并运行 PlantUML（需要 Java 环境）或 Mermaid-CLI（需要 Node.js 和 Puppeteer），会使部署变得非常笨重。

因此，建议采用 **Kroki (kroki.io)** 公共渲染服务：
Kroki 免费支持将各种文本图表（PlantUML, Mermaid, Excalidraw 等）转换为 PNG/SVG，不需要任何本地依赖，我们只需调用标准库的 `urllib.request` 发送网络请求即可实现渲染。

## 提出的修改方案

### 1. 核心渲染模块
#### [NEW] `src/blogger/core/diagrams.py`
创建图表生成核心功能，通过 POST 请求调用 `https://kroki.io/{diagram_type}/png`。
传入文本代码，直接将二进制图片流保存为本地 `.png` 文件。

### 2. MCP 服务端集成
#### [MODIFY] `src/blogger/mcp_server.py`
- 新增 MCP Tool: `@mcp.tool() def generate_diagram(diagram_type: str, code: str, output_path: str)`，允许 Claude/Gemini 等 Agent 直接调用该工具生成图片。
- 修改 `publish_article` 工具：添加可选参数 `cover_path` 和 `illustration_path`。当 Agent 准备好图片后，将图片绝对路径传给发布工具，服务端自动拷贝进 `payload_dir` 并写入 Markdown。

### 3. CLI 集成 (为 Bash Skill 保留)
#### [MODIFY] `src/blogger/cli.py`
使用 `argparse` 子命令重构现有的 CLI。
- `blogger publish --payload ...` (原来的默认行为)
- `blogger generate-diagram --type mermaid --input-file ./diagram.mmd --output ./cover.png` (新增，为终端模式的 Agent 提供绘图工具)

### 4. 规范与提示词更新
#### [MODIFY] `SKILL.md`
更新 `Step 2: 插图生成` 环节。
移除依赖外部本地 `claude` 子进程（Canva）的复杂描述，改为指示 Agent：
“利用你的代码生成能力编写 Mermaid 或 PlantUML，然后调用 `generate_diagram` (MCP) 或 `blogger generate-diagram` (CLI) 将其渲染为图片，并将其用于 Payload 中。”

---

> [!IMPORTANT]
> ## User Review Required / Open Questions
> 1. **关于公共 API**：这里计划使用免费的 `kroki.io`。它的优势是无需安装任何依赖，劣势是依赖网络和第三方服务。这符合项目的预期吗？
> 2. **CLI 结构重构**：为了加入生成图片的命令，CLI 从单一的 `blogger --payload xxx` 变成了子命令模式（`blogger publish --payload xxx` 和 `blogger generate-diagram ...`）。这是否可以接受？
