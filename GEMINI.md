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
