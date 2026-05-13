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
        self.chrome.set_file_input(t_idx, 'input[type="file"]', video_path)

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
        logger.info("Setting category to Tech/AI...")
        js_open_category = """
        (function() {
            const trigger = document.querySelector('.f-select-container');
            if (trigger) { trigger.click(); return "OPENED"; }
            return "NOT_FOUND";
        })();
        """
        if self.chrome.execute_javascript(w_idx, t_idx, js_open_category) == "OPENED":
            time.sleep(1.0)
            js_select_tech = """
            (function() {
                const tech = Array.from(document.querySelectorAll('.category-item')).find(el => el.innerText.includes('科技'));
                if (tech) { tech.click(); return "TECH_SELECTED"; }
                return "TECH_NOT_FOUND";
            })();
            """
            if self.chrome.execute_javascript(w_idx, t_idx, js_select_tech) == "TECH_SELECTED":
                time.sleep(0.5)
                js_select_ai = """
                (function() {
                    const ai = Array.from(document.querySelectorAll('.category-item')).find(el => el.innerText.includes('人工智能'));
                    if (ai) { ai.click(); return "AI_SELECTED"; }
                    return "AI_NOT_FOUND";
                })();
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_select_ai)

        # Extract tags
        tags_list = article_data.get("tags", ["AI", "Agent", "Architecture"])
        for tag in tags_list[:10]:
            logger.info(f"Adding tag: {tag}")
            js_focus_tag = """
            (function() {
                const tagInput = document.querySelector('.tag-container input');
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
                    delay 0.1
                    key code 36
                ''')
                time.sleep(0.5)

        # Description
        logger.info(f"Filling description: {desc[:50]}...")
        js_fill_desc = f"""
        (function() {{
            const desc = {json.dumps(desc)};
            const editor = document.querySelector('.video-desc .ql-editor');
            if (editor) {{
                editor.focus();
                editor.innerText = desc;
                editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return "DESC_SET";
            }}
            return "DESC_NOT_FOUND";
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_desc)
        
        if cover_path:
            logger.info(f"Uploading cover: {cover_path}")
            # Bilibili cover upload usually has its own input
            self.chrome.set_file_input(t_idx, '.cover-upload input[type="file"]', cover_path)
            time.sleep(2.0)

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
