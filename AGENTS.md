# Repository Guidelines

## Project Structure & Module Organization

- `src/blogger/`: Python package; `cli.py` exposes commands and `mcp_server.py` provides MCP integration.
- `src/blogger/core/`: Markdown parsing, browser controllers, diagram rendering, and cover/photo-card generation.
- `src/blogger/platforms/`: Platform-specific publishing adapters, including WeChat, Bilibili, Juejin, CSDN, Blogger, and Medium.
- `tests/`: Unit tests and manual browser diagnostics. Root-level `test_*.py` files are additional integration scripts.
- `skills/`: Agent workflows; `tools/`: rendering helpers, Chrome launchers, and a browser extension; `static/`: README images.
- `docs/`: Architecture, specifications, and implementation plans. Local `articles/`, `videos/`, and `screenshots/` are ignored by Git.

## Build, Test, and Development Commands

Run commands from the repository root, preferably in a virtual environment. Use Python 3.11+ because configuration imports `tomllib`, although package metadata declares Python 3.10+.

- `make install`: Install the package and dependencies in editable mode (`pip install -e .`).
- `blogger --help`: Inspect CLI commands; `blogger publish --help` shows publishing options.
- `blogger-mcp`: Start the MCP server.
- `python -m unittest discover -s tests -p 'test_photo_card_generator.py'`: Run photo-card tests; rendering tests require external tools, including macOS `sips`.
- `python -m pip install pytest`, then `python -m pytest tests/test_title_optimization.py`: Run function-based title tests.

`make test` and `make format` only print placeholder messages; they do not validate or format code.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` for modules/functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Follow surrounding code, add type hints where useful, and keep platform behavior in its adapter. No formatter or linter is configured.

## Testing Guidelines

Tests mix `unittest.TestCase`, plain assertions, and executable diagnostics; no coverage threshold is configured. Name tests `test_*.py` and test functions `test_*`. Add focused regression tests for behavior changes. Prefer temporary fixtures over personal article paths. Inspect browser/upload scripts before running them: some execute against live Chrome sessions at import time. Report missing fixtures or platform dependencies explicitly.

## Commit & Pull Request Guidelines

Follow the observed Conventional Commit pattern: `feat(skills): ...`, `fix(wechat): ...`, or `fix(parser): ...`. Keep changes focused. PRs should describe the behavior change, link relevant issues, and list validation results and limitations. Include screenshots for cover, photo-card, or editor changes. Update affected documentation and skills when workflows change.

## Configuration

`blogger.toml` defines account-specific collection names. Keep credentials, browser cookies, and private publishing payloads out of commits.
