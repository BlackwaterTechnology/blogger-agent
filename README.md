# Blogger Agent 🤖✍️

Blogger Agent is an intelligent automation project designed to seamlessly generate and publish articles to mainstream Chinese blog platforms. Provide a single topic or viewpoint, and the AI Agent takes care of writing the article and publishing it to platforms such as WeChat Official Accounts (微信公众号), Juejin (稀土掘金), and CSDN.

## 🎯 Vision

The ultimate goal of this project is to create a fully autonomous content creation and distribution pipeline:
1. **Topic Input**: You provide a topic, viewpoint, or a rough outline.
2. **AI Generation**: The agent leverages LLMs to research, outline, and draft a complete, high-quality Markdown article.
3. **Automated Publishing**: Through browser automation, the agent publishes the finalized article to multiple platforms without human intervention.

## 🚀 Features (Current & Planned)

- [x] **WeChat Official Account (微信公众号)**: Automated publishing using AppleScript and Chrome browser automation.
- [ ] **Juejin (稀土掘金)**: Automated publishing (Planned).
- [ ] **CSDN**: Automated publishing (Planned).
- [ ] **AI Article Generation**: Integration with LLMs (e.g., Claude, GPT-4, Gemini) to autonomously write content based on a prompt (Planned).
- [ ] **Multi-platform Orchestration**: Distribute a single article across multiple platforms with platform-specific formatting adjustments.

## 🛠 Architecture

Currently, the core publishing mechanism relies on:
*   **Python** for orchestration and Markdown parsing.
*   **Browser Automation** via `rookiepy` and `ChromeDomController` (AppleScript) to interact directly with existing Chrome sessions on macOS. This avoids the need for complex login simulations.

## 🔌 MCP Integration (Claude Code / Cursor / Codex / Gemini CLI)

This project acts as an **MCP (Model Context Protocol) Server**. You can install and use it directly inside modern AI IDEs and CLIs without manual Git cloning or dependency management. 

By leveraging `uvx`, the AI agent will securely download the code directly from GitHub, isolate the dependencies, and start the MCP server.

### For Claude Code
Run the following command in your Claude Code terminal:
```bash
claude mcp add blogger-agent uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger-mcp
```

### For Codex CLI
Run the native MCP add command in your terminal:
```bash
codex mcp add blogger-agent -- uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger-mcp
```

### For Gemini CLI
Add the server configuration to your `~/.gemini/settings.json` file:
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

Once added, the AI agent will natively have access to the `publish_article` tool. You can just ask: 
*"Write a technical article about Python Decorators and publish it to WeChat."*

## 🤖 Open Agent Skills Integration (2026 Standard)

If your Agent relies on the traditional `SKILL.md` instruction mechanism rather than MCP, you can install the Blogger Agent Skill using the 2026 Open Agent Skills Specification.

### 1. Universal Installation via GitHub CLI (Recommended)
GitHub's `gh skill` command is the standard way to distribute skills to compatible Agents. By default, the 2026 Open Agent Skills Specification defines `~/.agent/skills/` as the universal standard path. Platforms that natively follow this standard (such as **Antigravity**) require zero configuration.

```bash
# Install to the universal standard path (~/.agent/skills/)
gh skill install BlackwaterTechnology/blogger-agent

# Or target a specific Agent that uses a custom path
gh skill install BlackwaterTechnology/blogger-agent --agent claude-code
```

### 2. Agent-Specific Manual Installation

| Agent | Default Skill Path | Core Command |
| :--- | :--- | :--- |
| **Antigravity** 🌟 | `~/.agent/skills/` | `gh skill install BlackwaterTechnology/blogger-agent` |
| **OpenClaw** | `~/.openclaw/skills/` | `claw skill add BlackwaterTechnology/blogger-agent` |
| **Claude Code** | `~/.claude/skills/` | `gh skill install BlackwaterTechnology/blogger-agent --agent claude-code` |
| **Gemini CLI** | `$GEMINI_SKILLS_PATH` | `gemini skill install BlackwaterTechnology/blogger-agent` |
| **Codex** | `~/.../Codex/skills/` | Use IDE Plugin Market or `gh skill` |

> [!TIP]
> **Security Audit**: When installing skills from third-party repositories, you can use `gh skill audit BlackwaterTechnology/blogger-agent` to review the shell execution permissions requested by the `SKILL.md` before installation.

## 📦 Manual Installation & CLI Usage

If you prefer to run the script manually in your terminal without an AI Agent:

1. **Environment Setup**:
   ```bash
   make install
   ```

2. **Run Publishing Script (CLI Mode)**:
   ```bash
   blogger --payload test_data
   ```

## 🤝 Contributing

Contributions are welcome! If you're interested in adding support for a new platform like Juejin or CSDN, or implementing the AI generation layer, feel free to open a PR.
