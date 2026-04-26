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

## 🔌 Claude Code / MCP Integration

This project acts as an **MCP (Model Context Protocol) Server**. You can install and use it directly inside **Claude Code** or **Cursor** without manual Git cloning or dependency management.

### For Claude Code

Run the following command in your Claude Code terminal. It will use `uvx` to fetch the code from GitHub, isolate dependencies, and start the MCP server automatically:

```bash
claude mcp add blogger-agent uvx --from git+https://github.com/BlackwaterTechnology/blogger-agent.git blogger-mcp
```

Once added, Claude will natively have access to the `publish_article` tool. You can just ask Claude: 
*"Write a technical article about Python Decorators and publish it to WeChat."*

## 📦 Manual Installation & Usage

1. **Environment Setup**:
   ```bash
   make install
   ```

   *(Optional)* To install the Agent Skill locally for Antigravity:
   ```bash
   make install-skill
   ```

2. **Run Publishing Script (CLI Mode)**:
   ```bash
   blogger --payload test_data
   ```

## 🤝 Contributing

Contributions are welcome! If you're interested in adding support for a new platform like Juejin or CSDN, or implementing the AI generation layer, feel free to open a PR.
