# Blogger Skills

## Project Overview

`blogger` is an AI agent automation project. The ultimate vision of this project is to allow a user to provide a topic or viewpoint, from which an AI Agent will automatically generate a complete article and publish it to mainstream blog platforms such as WeChat Official Accounts (微信公众号), Juejin (稀土掘金), and CSDN.

Currently, the project focuses on the core capability of automating the publishing of local Markdown articles to WeChat Official Accounts. This standalone setup (originally extracted from `auto-register-accounts`) enables independent research, modular development, and cleaner codebase refinements towards the ultimate multi-platform AI agent vision.

## Architecture

This tool uses Python and AppleScript (via `ChromeDomController` and `rookiepy`) to interact with a running instance of Google Chrome on macOS. It parses Markdown files and uses browser automation to inject the content into the WeChat web editor.

## Directory Structure

*   **`publish.py`**: The main script to parse markdown content and orchestrate the publishing flow.
*   **`chrome.py`**: Contains `ChromeDomController`, which wraps AppleScript commands to manipulate Chrome tabs and DOM elements.
*   **`test_data/`**: Directory containing sample markdown articles and assets for testing the publishing flow.
*   **`requirements.txt`**: Python dependencies (`loguru`, `markdown`, `rookiepy`).

## Usage

1.  **Environment Setup**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Publishing Script**:
    ```bash
    python3 publish.py --payload test_data
    ```

## Development Context & Guidelines

*   **Migration**: This project was recently extracted from a larger framework. As such, some files may still contain legacy imports (e.g., `auto_register_framework`). These should be systematically replaced with standard Python equivalents or localized classes.
*   **No Framework Overhead**: Keep dependencies minimal and avoid re-introducing complex external frameworks for basic error handling or logging.
