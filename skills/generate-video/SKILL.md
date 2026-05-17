---
name: generate-video
description: Use when the user requests to generate, create, or render a video from documents, URLs, text, or research topics, or explicitly invokes /generate-video
---

# Video Generation

## Overview
Generates cinematic videos from provided sources using Google NotebookLM programmatic access.

## Core Workflow

1. **Authentication**
   Verify session: `notebooklm status`
   If needed: `notebooklm login --browser chrome --browser-cookies chrome`

2. **Preparation**
   - Create notebook: `notebooklm create "Video: [Topic]" --json`
   - Add sources: `notebooklm source add "[URL or path]" --json`
   - Wait for sources: `notebooklm source wait [source_id] -n [notebook_id]`

3. **Generation**
   Trigger generation (takes 15-45 mins):
   `notebooklm generate video --format cinematic "Instructions" --json`

4. **Background Download (Subagent)**
   DO NOT block the main thread. Dispatch a subagent (`@generalist`) with the following logic:
   - **Phase A (Initial Wait):** `sleep 600` (Wait 10 minutes, as cinematic videos never finish sooner).
   - **Phase B (Polling Loop):** Every 60 seconds, check status using `notebooklm artifact list -n {notebook_id} --json`.
   - **Phase C (Download):** Once `status` is `completed`, run `notebooklm download video ./videos/[topic]/video.mp4 -a {artifact_id} -n {notebook_id}`.

   **Example Subagent Prompt:**
   ```text
   Workflow for video {artifact_id} in notebook {notebook_id}:
   1. Initial wait: Run `sleep 600`.
   2. Polling loop:
      - Run `notebooklm artifact list -n {notebook_id} --json`.
      - Check if artifact {artifact_id} status is 'completed'.
      - If not, `sleep 60` and repeat.
      - Stop after 45 minutes total (max 35 polls).
   3. Finalize: Download to ./videos/[topic]/video.mp4.
   ```

5. **Post-Processing (Required)**
   - **Watermark Removal:** Execute the `watermark-remover` skill on the downloaded video to remove the AI-generated watermark.
   - **Cover Image:** Generate an infographic for the video cover:
     `notebooklm generate infographic --style professional --json`
     Wait for completion, then download and save as `cover.png` in the video's directory.
   - **Metadata:** Ask the notebook to generate a summary for publishing:
     ```bash
     notebooklm ask "为该视频写一段摘要和发布简介。要求：
     1. 必须严格使用以下Markdown结构输出（方便自动化脚本解析）：
     ### 标题：[纯文本标题]
     #### 【发布简介/文案】
     [正文...]
     
     2. 视频标题（Title）必须为纯文本，绝不能包含任何Emoji表情或特殊字符（如 🇯🇵、🎯 等）。"
     ```
     Save the output to `metadata.txt` in the video's directory. For WeChat publishing, match the metadata with collections defined in `blogger.toml`.

## Quick Reference

| Action | Command |
|---|---|
| Login | `notebooklm login --browser chrome --browser-cookies chrome` |
| Create Notebook | `notebooklm create "Title" --json` |
| Add Source | `notebooklm source add "URL/path" --json` |
| Wait for Source | `notebooklm source wait <id> -n <notebook_id>` |
| Generate Video | `notebooklm generate video --format cinematic "prompt" --json` |
| Generate Cover | `notebooklm generate infographic --style professional --json` |
| Wait for Artifact | `notebooklm artifact wait <id> -n <notebook_id>` |
| Download Video | `notebooklm download video ./path.mp4 -a <id> -n <notebook_id>` |

## Error Handling

- **GENERATION_FAILED:** Usually due to Google API rate limits. Wait 10 minutes and retry.
- **Auth/Cookie Error:** Session expired. Run `notebooklm auth check` and re-authenticate.
- **No notebook context:** Use `-n <notebook_id>` flag in parallel or automated workflows.
