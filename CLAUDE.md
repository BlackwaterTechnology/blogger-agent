# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`blogger` is a Python package that publishes locally-authored Markdown articles to Chinese blog platforms (WeChat Official Accounts, Juejin, CSDN) and short-video platforms (Bilibili, WeChat Channels) by **driving an already-running Google Chrome on macOS via AppleScript** — not via web APIs or headless browsers. The user must already be logged in to the target platform in Chrome; the tool finds the open tab and injects content.

It exposes the same logic through three surfaces:
- A CLI (`blogger`) for terminal/Bash agents
- An MCP server (`blogger-mcp`, FastMCP over stdio) for Claude Code / Cursor / Codex
- An Agent Skill (`skills/blogger-agent/SKILL.md`) for skill-aware agents

## Commands

```bash
make install          # pip install -e . — editable install
make install-skill    # copy SKILL.md to ~/.agent/skills/blogger-agent/
make clean            # remove __pycache__, *.egg-info, build/, dist/

# Publish (default command — args without a subcommand fall through to `publish`)
blogger --payload articles/<dir>/ --platform wechat,juejin,csdn

# Generate diagram via Kroki (no API key, hits kroki.io)
blogger generate-diagram --type mermaid --input foo.mmd --output foo.png

# Generate cinematic video via notebooklm-py and publish to short-video platforms
blogger video --payload articles/<dir>/ --platform bilibili,wechat_channels [--prompt "..."]

# Run MCP server (stdio transport — for IDE integration, not direct invocation)
blogger-mcp
```

There is no test runner or linter wired up. `make test` and `make format` are placeholders. `tests/` contains ad-hoc scripts (e.g. `test_dom.py`, `test_upload.py`) used during platform-automation development, not a pytest suite. `test_notebooklm.py` at the repo root is similarly a one-off probe.

`uv.lock` is committed; `notebooklm-py` is pulled directly from `git+https://github.com/xilu0/notebooklm-py.git` (see `[tool.uv.sources]` in `pyproject.toml`).

## Architecture

### Entry points dispatch to publishers
- `src/blogger/cli.py` — argparse front door. Note the backwards-compat shim: bare `--payload` (no subcommand) is rewritten to `publish --payload`. The `video` subcommand has its own flow (`handle_video`) that shells out to `uv run notebooklm` for video generation before dispatching to short-video publishers.
- `src/blogger/mcp_server.py` — FastMCP server exposing `publish_article` and `generate_diagram` tools. **It does not call publishers directly with the args**; it materializes a temp Markdown file in legacy heading-based format (`# 标题` / `# 简介` / `# 正文`), then re-parses it through `parse_markdown_payload`. Keep that round-trip in mind when changing the parser.

### The payload contract
`parse_markdown_payload` (`src/blogger/core/markdown_parser.py`) is the single source of truth for what publishers consume. Every publisher receives a `dict` with the same keys:
- `title`, `author`, `desc`, `collection`, `content`, `html_content`
- `cover_path` (Path | None) — the cover image
- `local_images` — every `![](...)` reference in the body that resolves to a local file, in document order. Publishers iterate this list to upload inline images.

Markdown input must use **YAML front matter** (`---`-fenced) with fields `title`, `author`, `desc`, `collection` (must be `"AI"` or `"Agent"`), and `cover` (filename relative to the payload dir; **required**). Inline images use native `![alt](filename.png)` — there's no separate `illustration` array anymore. The parser warns if `desc` is outside 60–120 chars (WeChat hard limit). Inline image markdown is rewritten to `[UPLOAD_IMAGE: <abs_path>]` placeholders that the WeChat publisher swaps in during posting.

The MCP server's temp-payload generator still writes the **legacy heading-based** format (`# 标题`, `# 作者`, ...) — but `parse_markdown_payload` now uses `python-frontmatter`, so the MCP path may be broken or relies on a fallback. If you touch this, verify both paths.

### Platforms layer
Each file in `src/blogger/platforms/` is one publisher class with a `publish(article_data: dict)` entry point:
- `wechat.py` (微信公众号) — the most mature; runs JS-driven UI state machines via `WechatPublisher.run_ui_state_machine` that poll JS evaluators returning `{state, action, is_done}`.
- `juejin.py`, `csdn.py` — same pattern.
- `bilibili.py`, `wechat_channels.py` — short-video targets, consume `article_data["video_path"]` from the `video` command.

To add a platform: drop a new module in `src/blogger/platforms/`, register it in both `cli.py`'s if/elif chain **and** `mcp_server.py`'s if/elif chain.

### Chrome automation core
`src/blogger/core/chrome.py` (`ChromeDomController`) and `jxa_chrome.py` are the macOS-specific glue. They use `osascript` (AppleScript) to find the right Chrome window/tab by URL prefix and run JS in the page context. **Critical constraint:** never interleave `execute_javascript` calls with `keystroke`/`key code` AppleScript actions on the same input — JXA invocation steals focus from Chrome's input field. See GEMINI.md for the full incident log.

### Diagram fallback
`core/diagrams.py` posts text to `kroki.io` and saves the returned PNG. Used when the agent has no native image-generation tool. SSL verification is intentionally disabled (`ctx.check_hostname = False`) for macOS compatibility.

## Where the deep platform-automation knowledge lives

**Read `GEMINI.md` before touching `csdn.py`, `wechat.py`, or any AppleScript/JXA code.** It contains the failure-mode catalog from the actual debugging sessions:
- CSDN tag input (`el-autocomplete`) — why `keystroke` fails and why `pbcopy` + `Cmd+V` works
- CSDN category panel — why clicking the outer `div` doesn't update Vue state and you must `click()` the `input.tag__option-chk` directly
- The general rule: **never mix AppleScript `keystroke` and `execute_javascript` in the same action sequence** (focus loss)

These lessons are not obvious from the code. The code reflects the *solution*; GEMINI.md captures *why* simpler approaches were rejected.

## Conventions

- **Default payload directory**: `articles/test_data/`. The CLI hardcodes a fallback file `ARC-AGI-文章.md` in `cli.py:63` if multiple `.md` files are present — be aware when renaming sample data.
- **Logging**: `loguru` everywhere. Don't introduce `logging` or `print`.
- **Image references**: Always relative to the payload dir, never absolute, in user-authored Markdown. Absolute paths only appear after parser rewriting.
- **`articles/` is gitignored** — generated payloads are user content, not code.
