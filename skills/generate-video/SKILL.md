---
name: generate-video
description: Generate cinematic narrative videos from documents, URLs, markdown articles, or research topics using Google NotebookLM (15-45 min asynchronous cloud generation with subagent polling). Use when the user requests cinematic video generation, long-form documentary/storytelling videos, or explicitly invokes /generate-video. For local lightweight dual-subtitle educational/listening videos, use dual-subtitle-video instead.
---

# Cinematic Video Generation (Google NotebookLM)

## Overview
Generates cinematic narrative videos from provided sources using Google NotebookLM programmatic access.

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
   - **Payload & Metadata:** Ask the notebook to generate publishing copy and format into `payload.md` in the video directory:
     ```bash
     notebooklm ask "为该视频写一段摘要和发布简介。要求：
     1. 标题（Title）：纯文本，绝不能包含任何Emoji表情或特殊字符（如 🇯🇵、🎯 等）。
     2. 摘要（Summary/desc）：控制在 60 到 120 字符之间。
     3. 正文文案：结构清晰，重点突出。"
     ```
     Create `payload.md` in the video's directory with standard YAML frontmatter:
     ```yaml
     ---
     title: "[纯文本标题]"
     author: "Gemini CLI"
     desc: "[60~120字摘要]"
     collection: "agent" # 必须匹配 blogger.toml 中的 video_collections
     cover: "cover.png"
     video: "video_clean.mp4"
     ---

     [完整发布文案/正文]
     ```

6. **Publishing (Next Step)**
   Once the payload is assembled, hand off to the `publish-video` skill to publish to target platforms:
   ```bash
   python3 -m src.blogger.cli publish \
     --payload videos/[topic]/payload.md \
     --platform wechat_video
   ```
   Or publish across multiple platforms (`wechat_video,wechat_channels,bilibili`).

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
