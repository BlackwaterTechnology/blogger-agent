# Bilibili Video Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement automated video publishing to Bilibili Creator Studio using CDP-based browser automation.

**Architecture:** A new `BilibiliPublisher` class leveraging `CdpChromeController` to interact with Bilibili's upload frame, handling file injection, metadata filling, and submission.

**Tech Stack:** Python, CDP (Chrome DevTools Protocol), Playwright-like DOM selectors.

---

### Task 1: Refactor BilibiliPublisher to use CDP

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Update imports and constructor**

```python
import time
import json
from loguru import logger
from ..core.cdp_chrome import CdpChromeController

class BilibiliPublisher:
    def __init__(self):
        self.chrome = CdpChromeController()
```

- [ ] **Step 2: Update tab finding and navigation**

```python
    def publish(self, article_data: dict, *, dry_run: bool = False) -> None:
        title = article_data.get("title", "")
        desc = article_data.get("desc", "")
        collection = article_data.get("collection", "Tech/AI")
        video_path = article_data.get("video_path")
        cover_path = article_data.get("cover_path")
        
        if not video_path:
            logger.error("No video_path provided.")
            return

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://member.bilibili.com/platform/upload/video/frame"])
        except Exception:
            raise SystemExit("Bilibili upload tab not found. Please open the upload page and retry.")
```

- [ ] **Step 3: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "refactor: switch BilibiliPublisher to CDP"
```

### Task 2: Implement Video Upload and Form Waiting

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Inject video file using CDP**

```python
        logger.info(f"Uploading video: {video_path}")
        self.chrome.set_file_input(t_idx, 'input[type="file"]', video_path)
        
        # Wait for form to load
        logger.info("Waiting for upload form to appear...")
        js_wait_form = """
        (function() {
            return !!document.querySelector('.video-title .input-val');
        })();
        """
        for _ in range(30):
            if self.chrome.execute_javascript(w_idx, t_idx, js_wait_form) == "true":
                break
            time.sleep(1.0)
```

- [ ] **Step 2: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "feat(bilibili): implement video file upload via CDP"
```

### Task 3: Implement Metadata Filling (Title, Type, Category)

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Implement basic metadata injection**

```python
        js_fill_basic = f"""
        (function() {{
            try {{
                const title = {json.dumps(title)};
                
                // 1. Title
                const titleInput = document.querySelector('.video-title .input-val');
                if (titleInput) {{
                    titleInput.value = title;
                    titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                // 2. Original Type (自制)
                const originalRadio = Array.from(document.querySelectorAll('.radio-item')).find(el => el.innerText.includes('自制'));
                if (originalRadio) originalRadio.click();
                
                return "SUCCESS";
            }} catch(e) {{ return e.message; }}
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_basic)
```

- [ ] **Step 2: Implement Category selection**

```python
        # Category handling (Tech/AI -> 科技/人工智能)
        js_fill_category = """
        (function() {
            try {
                const categoryTrigger = document.querySelector('.f-select-container');
                if (categoryTrigger) categoryTrigger.click();
                
                setTimeout(() => {
                    const tech = Array.from(document.querySelectorAll('.category-item')).find(el => el.innerText.includes('科技'));
                    if (tech) tech.click();
                    
                    setTimeout(() => {
                        const ai = Array.from(document.querySelectorAll('.category-item')).find(el => el.innerText.includes('人工智能'));
                        if (ai) ai.click();
                    }, 500);
                }, 500);
                return "CATEGORY_INITIATED";
            } catch(e) { return e.message; }
        })();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_category)
        time.sleep(2.0)
```

- [ ] **Step 3: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "feat(bilibili): fill title, type, and category"
```

### Task 4: Implement Tag and Description Handling

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Implement Tag injection**

```python
        # Extract tags from article_data or use defaults
        tags_list = article_data.get("tags", ["AI", "Agent", "Architecture"])
        for tag in tags_list[:10]:
            js_add_tag = f"""
            (function() {{
                const tagInput = document.querySelector('.tag-container input');
                if (tagInput) {{
                    tagInput.value = {json.dumps(tag)};
                    tagInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return "READY_FOR_ENTER";
                }}
                return "NOT_FOUND";
            }})();
            """
            if self.chrome.execute_javascript(w_idx, t_idx, js_add_tag) == "READY_FOR_ENTER":
                self.chrome.run_in_chrome_process('key code 36') # Enter
                time.sleep(0.5)
```

- [ ] **Step 2: Implement Description injection**

```python
        js_fill_desc = f"""
        (function() {{
            const desc = {json.dumps(desc)};
            const editor = document.querySelector('.video-desc .ql-editor');
            if (editor) {{
                editor.innerText = desc;
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return "DESC_SET";
            }}
            return "DESC_NOT_FOUND";
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_desc)
```

- [ ] **Step 3: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "feat(bilibili): add tags and description"
```

### Task 5: Implement Cover Upload and Submission

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Implement Cover upload**

```python
        if cover_path:
            logger.info(f"Uploading cover: {cover_path}")
            # Bilibili cover upload usually has its own input
            self.chrome.set_file_input(t_idx, '.cover-upload input[type="file"]', cover_path)
            time.sleep(2.0)
```

- [ ] **Step 2: Implement Final Submission**

```python
        if not dry_run:
            logger.info("Submitting Bilibili video...")
            js_submit = """
            (function() {
                const btn = Array.from(document.querySelectorAll('.submit-container .bcc-button')).find(el => el.innerText.includes('立即投稿'));
                if (btn) {
                    btn.click();
                    return "SUBMITTED";
                }
                return "SUBMIT_BTN_NOT_FOUND";
            })();
            """
            self.chrome.execute_javascript(w_idx, t_idx, js_submit)
        else:
            logger.info("Dry-run: skipping submission.")
```

- [ ] **Step 3: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "feat(bilibili): implement cover upload and submission"
```

### Task 6: Register Bilibili in CLI and MCP

**Files:**
- Modify: `src/blogger/cli.py`
- Modify: `src/blogger/mcp_server.py`

- [ ] **Step 1: Register in CLI**

```python
# src/blogger/cli.py
from .platforms.bilibili import BilibiliPublisher
# ... inside the platform mapping ...
"bilibili": BilibiliPublisher,
```

- [ ] **Step 2: Register in MCP**

```python
# src/blogger/mcp_server.py
# ... inside publish_article tool ...
if platform == "bilibili":
    from .platforms.bilibili import BilibiliPublisher
    BilibiliPublisher().publish(article_data, dry_run=dry_run)
```

- [ ] **Step 3: Commit**

```bash
git add src/blogger/cli.py src/blogger/mcp_server.py
git commit -m "feat: register bilibili platform in CLI and MCP"
```

### Task 7: End-to-End Verification

- [ ] **Step 1: Run the publisher for Bilibili**

Run: `uv run blogger --payload videos/architecting-agentic-memory/ --platform bilibili --dry-run`
Expected: Video uploads, metadata is filled, cover is set, and it stops before submission.

- [ ] **Step 2: Final Verification**
Check the browser tab to ensure everything is correct.
