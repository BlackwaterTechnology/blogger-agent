# Blogger Agent 🤖✍️

> **🌐 语言**: [English](README.md) · **简体中文**

Blogger Agent 是一个面向中文创作场景的自动化项目：你给一个选题或观点，Agent 负责把文章写出来，再自动发布到主流博客平台 —— 微信公众号、稀土掘金、CSDN。整个写作 + 排版 + 多端发布的流水线由 AI 驱动，目标是让创作者把精力放在「想表达什么」，发布过程交给 Agent。

## 🌟 实际效果 / 一键关注

想看看用这个项目产出的文章长什么样？微信公众号 **「运维开发与AI实战」** 上的每一篇都由本项目端到端生成并发布 —— 它本身就是 Blogger Agent 的最佳 Demo。

<p align="center">
  <img src="static/wechat-official-account.png" alt="微信公众号「运维开发与AI实战」二维码" width="240" />
  <br />
  <em>扫码关注公众号「运维开发与AI实战」</em>
</p>

## 🎯 项目愿景

我们想搭一条全自动的内容生产 + 分发流水线：

1. **输入选题**：你只提供一个话题、观点或粗略大纲。
2. **AI 生成**：Agent 调用 LLM 完成调研、列大纲、写出完整的高质量 Markdown 草稿。
3. **自动发布**：通过浏览器自动化，无人值守地把成稿同步到多个平台。

## 🚀 功能进度

- [x] **微信公众号**：基于 AppleScript + Chrome 自动化的发布通路。
- [x] **稀土掘金**：自动发布(已实现)。
- [x] **CSDN**:自动发布(规划中)。
- [x] **AI 写稿**:接入 Claude / GPT-4 / Gemini 等 LLM,根据 prompt 自主成稿(规划中)。
- [ ] **多端编排**:同一篇文章按各平台格式差异化排版后并行发布。

## 🛠 架构概览

当前的发布机制依赖:

* **Python** 负责调度和 Markdown 解析。
* **浏览器自动化**:通过 `rookiepy` + `ChromeDomController`(AppleScript)直接驱动 macOS 上已经登录的 Chrome 会话,绕开复杂的登录模拟。

## 🔌 MCP 集成(Claude Code / Cursor / Codex / Gemini CLI)

本项目同时是一个 **MCP(Model Context Protocol)Server**,你可以在主流 AI IDE 和 CLI 中直接挂载使用,不需要手动 git clone、不用管依赖。

借助 `uvx`,Agent 会从 GitHub 安全拉取代码、隔离依赖、启动 MCP server。

### Claude Code

在 Claude Code 终端里运行:

```bash
claude mcp add blogger-agent uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger-mcp
```

### Codex CLI

在终端里运行 MCP add 命令:

```bash
codex mcp add blogger-agent -- uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger-mcp
```

### Gemini CLI

把以下配置加到 `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "blogger-agent": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/BlackwaterTechnology/blogger-agent.git", "blogger-mcp"]
    }
  }
}
```

挂载完成后,Agent 就原生拥有 `publish_article` 工具,直接对它说:
*「写一篇讲 Python Decorators 的技术文章,然后发布到微信公众号。」*

## 🤖 Open Agent Skills 集成(2026 标准)

如果你的 Agent 用的是传统 `SKILL.md` 指令机制而不是 MCP,可以按照 2026 Open Agent Skills 规范来安装本 Skill。

### 1. 通过 GitHub CLI 通用安装(推荐)

`gh skill` 是把 Skill 分发到兼容 Agent 的标准命令。2026 规范默认把 `~/.agent/skills/` 作为通用路径,原生兼容该规范的平台(例如 **Antigravity**)零配置可用。

```bash
# 安装到通用标准路径(~/.agent/skills/)
gh skill install BlackwaterTechnology/blogger-agent

# 或者指定使用自定义路径的 Agent
gh skill install BlackwaterTechnology/blogger-agent --agent claude-code
```

### 2. 各 Agent 的手动安装

| Agent | 默认 Skill 路径 | 安装命令 |
| :--- | :--- | :--- |
| **Antigravity** 🌟 | `~/.agent/skills/` | `gh skill install BlackwaterTechnology/blogger-agent` |
| **OpenClaw** | `~/.openclaw/skills/` | `claw skill add BlackwaterTechnology/blogger-agent` |
| **Claude Code** | `~/.claude/skills/` | `gh skill install BlackwaterTechnology/blogger-agent --agent claude-code` |
| **Gemini CLI** | `$GEMINI_SKILLS_PATH` | `gemini skill install BlackwaterTechnology/blogger-agent` |
| **Codex** | `~/.../Codex/skills/` | 用 IDE 插件市场或 `gh skill` |

> [!TIP]
> **安全审计**:从第三方仓库装 Skill 时,可以先跑 `gh skill audit BlackwaterTechnology/blogger-agent`,审一下 `SKILL.md` 里申请的 shell 执行权限。

## 📦 手动安装与 CLI 用法

如果你不想接 Agent,只想在终端手动跑:

1. **环境准备**:
   ```bash
   make install
   ```

2. **CLI 模式发布**:
   ```bash
   blogger --payload articles/test_data/ --platform {wechat,juejin,csdn}
   ```

## 🖼 图表渲染依赖(可选但推荐)

`blogger-agent` skill 默认优先用 **本地离线渲染**,实在不行才回退到公开的 `kroki.io`(隐私更好,也不会撞 504)。如果你打算写带 Mermaid / PlantUML / 数据图的文章,一次性装好这几样工具:

| 工具 | 作用 | 安装 |
|---|---|---|
| **mmdc** (`@mermaid-js/mermaid-cli`) | Mermaid `.mmd` → PNG/SVG,官方 Dagre 布局 | `npm install -g @mermaid-js/mermaid-cli`(会顺带拉 Puppeteer 的 Chromium,约 200MB) |
| **plantuml.jar** | PlantUML `.puml` → SVG,思维导图 / 组件图 / 时序图 | `curl -sSL -o ~/bin/plantuml.jar https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar` |
| **librsvg** (`rsvg-convert`) | SVG → 高分辨率 PNG(通用后处理) | `brew install librsvg` |
| **matplotlib** | 饼图 / 柱状图 / 数据可视化,主题和尺寸可控 | `pip install matplotlib`(多数 Python 环境已自带) |

PlantUML 需要 Java(没装就 `brew install openjdk`)。mmdc 需要 Node ≥ 18.19。

**为什么先用本地?** 老的 `blogger generate-diagram` 命令把源码 POST 给 `kroki.io`,偶尔会被限流或返回 504。本地渲染不用上公网,而且 mmdc 和 `mermaid.live` 用的是同一套 Dagre 布局。

### 封面比例工具(跨平台)

跨平台博客封面(微信公众号 / 掘金 / CSDN)用 **16:9**(横向流程图 / 对比图 / 时间线)或 **1:1**(海报 / 概念图 / 中心放射)效果最好,各平台会自动按自己的缩略图规格裁剪。原来那条 2.35:1 只对微信头条生效,现在的编辑器都接受 16:9。任何来源生成的 `cover.png` 渲染完之后,都跑一遍这个工具做一次归一化:

```bash
# 16:9 横版(默认)
python3 tools/fit_wechat_cover.py path/to/cover.png --width 1920

# 1:1 方版(微信次条 / 海报封面用)
python3 tools/fit_wechat_cover.py path/to/cover.png --ratio 1 --width 1500
```

工具会把封面 letterbox 进目标画布(白底,不裁切、不拉伸)。把它放在每次封面渲染流程的**最后一步**。

完整渲染规范 —— 比例规则、配色、常见坑 —— 见 `skills/blogger-agent/SKILL.md` 阶段 2。

## 👤 关于作者 / 一起聊聊

我平时写 DevOps × AI Agent、Harness 工程、平台自动化方向的内容。如果你觉得这个项目对你有用,下面这些地方可以找到我,也欢迎一起讨论:

| 渠道 | 地址 |
| :--- | :--- |
| 📣 微信公众号 | **运维开发与AI实战**([扫上面那个二维码](#-实际效果--一键关注))—— 本工具的真实落地场景 |
| 📝 CSDN 博客 | <https://yijie.blog.csdn.net> |
| 📝 稀土掘金 | <https://juejin.cn/user/4151367379457848> |

想直接交流,或者加读者 / 贡献者交流群?加我个人微信:

<p align="center">
  <img src="static/wechat-personal.png" alt="个人微信二维码" width="240" />
  <br />
  <em>扫码加我微信 · 备注「进群」拉你进交流群</em>
</p>

## 🤝 共建

欢迎 PR!想加新平台(比如完善 Juejin / CSDN 通路),或者把 AI 写稿那一层接进来,直接开 PR 就行。
