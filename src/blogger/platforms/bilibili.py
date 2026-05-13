import time
import json
import subprocess
from loguru import logger
from ..core.cdp_chrome import CdpChromeController

class BilibiliPublisher:
    def __init__(self):
        self.chrome = CdpChromeController()

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
            w_idx, t_idx = self.chrome.find_global_tab(["https://member.bilibili.com/platform/upload/video"])
        except Exception:
            raise SystemExit("Bilibili upload tab not found. Please open the upload page and retry.")

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

        # Wait for form to load
        logger.info("Waiting for upload form to appear...")
        js_wait_form = """
        (function() {
            return !!document.querySelector('.video-title .input-val');
        })();
        """
        form_found = False
        for _ in range(30):
            res = self.chrome.execute_javascript(w_idx, t_idx, js_wait_form)
            if res == "True" or res == "true":
                form_found = True
                break
            time.sleep(1.0)
            
        if not form_found:
            logger.error("Upload form did not appear after 30 seconds. Video may still be processing or selector changed.")
            return

        logger.info(f"Filling metadata: {title}")
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

        # Category handling (Tech/AI -> 科技/人工智能)
        logger.info(f"Setting category to {collection}...")
        
        # Mapping for common categories
        cat_map = {
            "Tech/AI": ["科技", "人工智能"],
            "Tech/Code": ["科技", "计算机技术"],
            "Tech/Software": ["科技", "计算机技术"],
            "Life": ["生活", "日常"],
        }
        
        target_cats = cat_map.get(collection, ["科技", "人工智能"])
        
        js_open_category = """
        (function() {
            const trigger = document.querySelector('.f-select-container') || document.querySelector('.category-select-content');
            if (trigger) { trigger.click(); return "OPENED"; }
            return "NOT_FOUND";
        })();
        """
        if self.chrome.execute_javascript(w_idx, t_idx, js_open_category) == "OPENED":
            time.sleep(1.0)
            for cat_name in target_cats:
                js_select_cat = f"""
                (function() {{
                    const items = Array.from(document.querySelectorAll('.category-item, .f-select-item'));
                    const item = items.find(el => el.innerText.includes('{cat_name}'));
                    if (item) {{ item.click(); return "SELECTED"; }}
                    return "NOT_FOUND";
                }})();
                """
                res = self.chrome.execute_javascript(w_idx, t_idx, js_select_cat)
                logger.info(f"Selecting {cat_name}: {res}")
                time.sleep(0.8)

        # Extract tags
        tags_list = article_data.get("tags", ["AI", "Agent", "Architecture"])
        for tag in tags_list[:10]:
            logger.info(f"Adding tag: {tag}")
            js_focus_tag = """
            (function() {
                const tagInput = document.querySelector('.tag-container input') || document.querySelector('.tag-input input');
                if (tagInput) {
                    tagInput.focus();
                    tagInput.click();
                    return "FOCUSED";
                }
                return "NOT_FOUND";
            })();
            """
            if self.chrome.execute_javascript(w_idx, t_idx, js_focus_tag) == "FOCUSED":
                # Use clipboard paste to bypass autocomplete issues (Lesson 1/2)
                subprocess.run(["pbcopy"], input=tag.encode(), check=True)
                self.chrome.run_in_chrome_process('''
                    keystroke "a" using {command down}
                    delay 0.1
                    keystroke "v" using {command down}
                    delay 0.2
                    key code 36
                ''')
                time.sleep(0.8)

        # Description
        logger.info(f"Filling description: {desc[:50]}...")
        js_fill_desc = f"""
        (function() {{
            const desc = {json.dumps(desc)};
            const editor = document.querySelector('.video-desc .ql-editor') || document.querySelector('.bcc-textarea-container textarea');
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
            res = self.chrome.execute_javascript(w_idx, t_idx, js_submit)
            logger.info(f"Submission result: {res}")
        else:
            logger.info("Dry-run: skipping submission.")

        logger.info("Metadata filled.")
