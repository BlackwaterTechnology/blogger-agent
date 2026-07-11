# Design Spec: Bilibili Video Publisher Integration

**Date:** 2026-05-13
**Status:** Draft
**Topic:** Bilibili Platform Support

## 1. Overview
Add Bilibili video publishing support to the `blogger-agent` project. This enables agents to automatically upload video content, set metadata (title, tags, category, description), and upload covers to Bilibili's Creator Studio.

## 2. Architecture
The integration will follow the existing project pattern for platforms:
- **Core Driver:** `CdpChromeController` (CDP-based automation).
- **Publisher Class:** `BilibiliPublisher` in `src/blogger/platforms/bilibili.py`.
- **UI Management:** `run_ui_state_machine` to handle asynchronous loading and state transitions.

## 3. Implementation Details

### 3.1 `BilibiliPublisher` Logic
- **Tab Selection:** Target `https://member.bilibili.com/platform/upload/video/frame`.
- **Video Upload:** 
    - Use `self.chrome.set_file_input('input[type="file"]', video_path)`.
    - This triggers the upload process immediately.
- **Form Filling:**
    - **Wait:** Poll for `.video-title .input-val` to ensure the form is rendered.
    - **Title:** Set value of `.video-title .input-val`.
    - **Type:** Click radio button for "自制" (Original).
    - **Category:** 
        - Click the category selector.
        - Click "科技".
        - Click "人工智能".
    - **Tags:** 
        - Enter tags into the tag input field.
        - Handle Bilibili's tag entry (usually requires Enter after each tag).
    - **Description:** 
        - Target the Quill editor `.video-desc .ql-editor`.
        - Inject text via `innerText` and trigger input events.
    - **Cover:** 
        - Locate the cover upload input.
        - Use `set_file_input` with `cover_path`.
- **Submission:**
    - Click `button:contains("立即投稿")`.
    - Support `dry_run` to skip this final step.

### 3.2 Metadata Mapping
- **Source:** `metadata.txt` (or `article_data` passed via MCP/CLI).
- **Title:** Prefer Juejin/CSDN title.
- **Description:** Prefer the detailed summary section.
- **Tags:** Extract common tags across platforms.

### 3.3 Integration Points
- **CLI (`src/blogger/cli.py`):** Register `bilibili` platform.
- **MCP (`src/blogger/mcp_server.py`):** Add `bilibili` to the `publish_article` tool.

## 4. Testing & Verification
- **Test Case:** Publish `videos/architecting-agentic-memory/video.mp4`.
- **Validation:** 
    - Verify video upload starts.
    - Verify all metadata fields are correctly populated.
    - Verify cover image is uploaded.
    - Final verification on the Bilibili Creator Studio draft page.

## 5. Scope & Constraints
- Only supports macOS with Chrome installed.
- Requires Chrome to be launched with remote debugging enabled (`tools/launch-chrome-cdp.sh`).
- Assumes the user is already logged in to Bilibili in the CDP browser instance.
