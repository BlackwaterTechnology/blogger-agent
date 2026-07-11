# Bilibili Publisher Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix video/cover upload confusion, implement cover upload dialog interaction, and improve metadata/collection handling for Bilibili.

**Architecture:** Refine `BilibiliPublisher` to precisely target file inputs and handle multi-step UI interactions (dialogs).

**Tech Stack:** Python, CDP, JavaScript.

---

### Task 1: Fix Video vs. Cover Upload confusion

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Precisely target video upload input**

```python
        logger.info(f"Uploading video: {video_path}")
        # Target the input specifically inside the video entrance
        js_video_input = """
        (function() {
            const videoInput = Array.from(document.querySelectorAll('input[type="file"]')).find(i => i.accept && i.accept.includes('video'));
            if (videoInput) {
                const tempId = "video_upload_input_" + Date.now();
                videoInput.id = tempId;
                return "#" + tempId;
            }
            return 'input[type="file"]'; // fallback
        })();
        """
        video_selector = self.chrome.execute_javascript(w_idx, t_idx, js_video_input)
        self.chrome.set_file_input(t_idx, video_selector, video_path)
```

- [ ] **Step 2: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "fix(bilibili): precisely target video file input"
```

### Task 2: Implement Cover Upload Dialog Interaction

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Implement multi-step cover upload**

```python
        if cover_path:
            logger.info(f"Uploading cover: {cover_path}")
            
            # 1. Click "封面设置" (Cover Setup)
            js_open_cover = """
            (function() {
                const btn = Array.from(document.querySelectorAll('div, span, button')).find(el => el.innerText && el.innerText.includes('封面设置'));
                if (btn) { btn.click(); return "CLICKED"; }
                return "NOT_FOUND";
            })();
            """
            if self.chrome.execute_javascript(w_idx, t_idx, js_open_cover) == "CLICKED":
                time.sleep(1.5)
                
                # 2. Click "上传封面" (Upload Cover) inside dialog
                js_click_upload = """
                (function() {
                    const btn = Array.from(document.querySelectorAll('.bcc-dialog div, .bcc-dialog span, .bcc-dialog button')).find(el => el.innerText && el.innerText.includes('上传封面'));
                    if (btn) { btn.click(); return "CLICKED"; }
                    return "NOT_FOUND";
                })();
                """
                if self.chrome.execute_javascript(w_idx, t_idx, js_click_upload) == "CLICKED":
                    time.sleep(1.0)
                    
                    # 3. Find the input[type="file"] in the dialog and set file
                    js_find_dialog_input = """
                    (function() {
                        const dialog = document.querySelector('.bcc-dialog');
                        if (!dialog) return "NO_DIALOG";
                        const input = dialog.querySelector('input[type="file"]');
                        if (input) {
                            const tempId = "cover_dialog_input_" + Date.now();
                            input.id = tempId;
                            return "#" + tempId;
                        }
                        return "NO_INPUT";
                    })();
                    """
                    cover_selector = self.chrome.execute_javascript(w_idx, t_idx, js_find_dialog_input)
                    if cover_selector.startswith("#"):
                        self.chrome.set_file_input(t_idx, cover_selector, cover_path)
                        time.sleep(2.0)
                        
                        # 4. Click "完成" or "确定" in the cropper dialog
                        js_confirm_cover = """
                        (function() {
                            const btn = Array.from(document.querySelectorAll('.bcc-dialog button')).find(el => el.innerText && (el.innerText.includes('完成') || el.innerText.includes('确定')));
                            if (btn) { btn.click(); return "CONFIRMED"; }
                            return "NOT_FOUND";
                        })();
                        """
                        self.chrome.execute_javascript(w_idx, t_idx, js_confirm_cover)
```

- [ ] **Step 2: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "feat(bilibili): implement cover upload via dialog interaction"
```

### Task 3: Fix Description and Collection Handling

**Files:**
- Modify: `src/blogger/platforms/bilibili.py`

- [ ] **Step 1: Improve description injection**

```python
        # Description (简介)
        logger.info(f"Filling description: {desc[:50]}...")
        js_fill_desc = f"""
        (function() {{
            const desc = {json.dumps(desc)};
            // Bilibili uses Quill editor or a standard textarea
            const editor = document.querySelector('.video-desc .ql-editor') || 
                           document.querySelector('.bcc-textarea-container textarea') ||
                           document.querySelector('textarea[placeholder*=\"简介\"]');
            if (editor) {{
                editor.focus();
                if (editor.tagName === 'TEXTAREA') {{
                    editor.value = desc;
                }} else {{
                    editor.innerText = desc;
                }}
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return "DESC_SET";
            }}
            return "DESC_NOT_FOUND";
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_desc)
```

- [ ] **Step 2: Implement Collection (Series) selection**

```python
        # Collection (加入合集)
        if collection:
            logger.info(f"Adding to collection: {collection}")
            js_open_series = """
            (function() {
                const btn = Array.from(document.querySelectorAll('.app_wrap div, .app_wrap span')).find(el => el.innerText && el.innerText.includes('加入合集'));
                if (btn) { btn.click(); return "OPENED"; }
                return "NOT_FOUND";
            })();
            """
            if self.chrome.execute_javascript(w_idx, t_idx, js_open_series) == "OPENED":
                time.sleep(1.0)
                # Search and select
                js_select_series = f"""
                (function() {{
                    const collectionName = {json.dumps(collection)};
                    const items = Array.from(document.querySelectorAll('.bcc-select-item, .series-item'));
                    const item = items.find(el => el.innerText && el.innerText.includes(collectionName));
                    if (item) {{
                        item.click();
                        return "SELECTED";
                    }}
                    return "NOT_FOUND";
                }})();
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_select_series)
```

- [ ] **Step 3: Commit**

```bash
git add src/blogger/platforms/bilibili.py
git commit -m "feat(bilibili): improve description and collection handling"
```

### Task 4: Final Verification

- [ ] **Step 1: Run end-to-end verification**

Run: `uv run blogger publish --payload videos/architecting-agentic-memory/ --platform bilibili --no-publish`
Expected: Video uploads, cover dialog opens and uploads image, description is filled, collection is selected.
