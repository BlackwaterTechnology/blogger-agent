import time
import json
import base64
import re
import mimetypes
import subprocess
from pathlib import Path
from loguru import logger
import markdown
from ..core.cdp_chrome import CdpChromeController

class BloggerPublisher:
    def __init__(self):
        self.chrome = CdpChromeController()

    def convert_to_html_with_base64_images(self, content: str, payload_dir: Path) -> str:
        # Find all markdown images: ![alt](path)
        def replacer(match):
            alt = match.group(1)
            src = match.group(2)
            if src.startswith('http://') or src.startswith('https://') or src.startswith('data:'):
                return match.group(0)
            
            local_path = payload_dir / src
            if local_path.exists():
                try:
                    mime_type, _ = mimetypes.guess_type(str(local_path))
                    if not mime_type:
                        mime_type = "image/png"
                    with open(local_path, "rb") as img_file:
                        b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                    logger.info(f"Converted inline image {src} to base64 ({len(b64_data)} chars)")
                    return f'![{alt}](data:{mime_type};base64,{b64_data})'
                except Exception as e:
                    logger.warning(f"Failed to encode image {src} to base64: {e}")
                    return match.group(0)
            return match.group(0)
            
        # Replace image paths with base64 data URIs
        converted_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replacer, content)
        
        # Also replace HTML img tags if any: <img src="path" ...>
        def html_img_replacer(match):
            attrs = match.group(1)
            src_match = re.search(r'src=["\'](.*?)["\']', attrs)
            if not src_match:
                return match.group(0)
            src = src_match.group(1)
            if src.startswith('http://') or src.startswith('https://') or src.startswith('data:'):
                return match.group(0)
            
            local_path = payload_dir / src
            if local_path.exists():
                try:
                    mime_type, _ = mimetypes.guess_type(str(local_path))
                    if not mime_type:
                        mime_type = "image/png"
                    with open(local_path, "rb") as img_file:
                        b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                    new_src = f'data:{mime_type};base64,{b64_data}'
                    new_attrs = attrs.replace(src, new_src)
                    logger.info(f"Converted HTML img {src} to base64")
                    return f'<img {new_attrs}>'
                except Exception as e:
                    logger.warning(f"Failed to encode html img {src} to base64: {e}")
                    return match.group(0)
            return match.group(0)
            
        converted_content = re.sub(r'<img\s+([^>]*?)>', html_img_replacer, converted_content)
        
        # Convert markdown to html
        html = markdown.markdown(converted_content, extensions=['fenced_code', 'tables', 'sane_lists'])
        return html

    def ensure_html_view(self, w_idx: int, t_idx: str) -> bool:
        js_check = """
        (function() {
            const cmEl = document.querySelector('.CodeMirror');
            if (cmEl && cmEl.offsetWidth > 0 && cmEl.offsetHeight > 0) {
                return "ALREADY_HTML";
            }
            return "NEED_SWITCH";
        })();
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_check)
        if res == "ALREADY_HTML":
            return True
            
        # Open dropdown
        self.chrome.execute_javascript(w_idx, t_idx, """
        (function() {
            const toggleBtn = document.querySelector('div[aria-label="Toggle view"]');
            if (toggleBtn) toggleBtn.click();
        })();
        """, settle_seconds=0.5)
        
        # Select option
        self.chrome.execute_javascript(w_idx, t_idx, """
        (function() {
            const options = Array.from(document.querySelectorAll('div[role="option"]'));
            const htmlOption = options.find(o => o.innerText.includes('HTML view') || o.innerText.includes('HTML 视图'));
            if (htmlOption) htmlOption.click();
        })();
        """, settle_seconds=2.0)
        
        res = self.chrome.execute_javascript(w_idx, t_idx, js_check)
        return res == "ALREADY_HTML"

    def ensure_compose_view(self, w_idx: int, t_idx: str) -> bool:
        js_check = """
        (function() {
            const iframe = document.querySelector('iframe.editable');
            if (iframe && iframe.offsetWidth > 0 && iframe.offsetHeight > 0) {
                return "ALREADY_COMPOSE";
            }
            return "NEED_SWITCH";
        })();
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_check)
        if res == "ALREADY_COMPOSE":
            return True
            
        # Open dropdown
        self.chrome.execute_javascript(w_idx, t_idx, """
        (function() {
            const toggleBtn = document.querySelector('div[aria-label="Toggle view"]');
            if (toggleBtn) toggleBtn.click();
        })();
        """, settle_seconds=0.5)
        
        # Select option
        self.chrome.execute_javascript(w_idx, t_idx, """
        (function() {
            const options = Array.from(document.querySelectorAll('div[role="option"]'));
            const composeOption = options.find(o => o.innerText.includes('Compose view') || o.innerText.includes('撰写视图'));
            if (composeOption) composeOption.click();
        })();
        """, settle_seconds=2.0)
        
        res = self.chrome.execute_javascript(w_idx, t_idx, js_check)
        return res == "ALREADY_COMPOSE"

    def publish(self, article_data: dict, *, dry_run: bool = False) -> None:
        title = article_data.get("title", "")
        content = article_data.get("content", "")
        collection = article_data.get("collection", "")
        
        # Resolve payload directory
        payload_path = article_data.get("payload_path")
        if payload_path:
            payload_dir = Path(payload_path).parent
        else:
            payload_dir = Path.cwd()
            
        # 1. Find Blogger tab (editor or dashboard page)
        try:
            w_idx, t_idx = self.chrome.find_global_tab([
                "https://www.blogger.com/blog/post/edit",
                "https://www.blogger.com/blog/posts"
            ])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(
                f"Blogger tab not found in Chrome. Open Blogger (blogger.com) "
                f"in a logged-in tab and retry. Detail: {e}"
            )
            
        logger.info(f"Found Blogger tab: {url}")
        
        # 2. Check if on dashboard and need to create a new post
        if "post/edit" not in url:
            logger.info("Not currently on the editor page. Clicking 'Create New Post'...")
            js_click_new = """
            (function() {
                const btn = document.querySelector('div[aria-label="Create New Post"]');
                if (btn) {
                    btn.click();
                    return "CLICKED";
                }
                return "NOT_FOUND";
            })();
            """
            click_res = self.chrome.execute_javascript(w_idx, t_idx, js_click_new, settle_seconds=0.5)
            if click_res != "CLICKED":
                logger.warning("Could not find 'Create New Post' button. Navigating directly...")
                match = re.search(r'posts/(\d+)', url)
                if match:
                    blog_id = match.group(1)
                    self.chrome.set_tab_url(w_idx, t_idx, f"https://www.blogger.com/blog/post/edit/{blog_id}/new", settle_seconds=2.0)
                else:
                    raise SystemExit("Failed to create a new post: no blog ID found in URL and click failed.")
            
            logger.info("Waiting for editor to load...")
            js_check_editor = """
            (function() {
                const titleInput = document.querySelector('input[aria-label="Title"]');
                const toggleBtn = document.querySelector('div[aria-label="Toggle view"]');
                if (titleInput && toggleBtn) {
                    return "LOADED";
                }
                return "LOADING";
            })();
            """
            editor_loaded = False
            for _ in range(15):
                try:
                    res = self.chrome.execute_javascript(w_idx, t_idx, js_check_editor, settle_seconds=0.5)
                    if res == "LOADED":
                        editor_loaded = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)
                
            if not editor_loaded:
                raise SystemExit("Blogger editor failed to load in time.")
                
        # 3. Set Title
        js_set_title = f"""
        (function() {{
            const titleInput = document.querySelector('input[aria-label="Title"]');
            if (titleInput) {{
                titleInput.value = {json.dumps(title)};
                titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                titleInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return "SET";
            }}
            return "NOT_FOUND";
        }})();
        """
        logger.info(f"Setting title: {title}")
        self.chrome.execute_javascript(w_idx, t_idx, js_set_title, settle_seconds=0.5)
        
        # 4. Set Labels/Tags
        if collection:
            logger.info(f"Setting labels: {collection}")
            js_set_labels = f"""
            (function() {{
                const labelTextarea = document.querySelector('textarea[aria-label="Separate labels by commas"]');
                if (labelTextarea) {{
                    labelTextarea.value = {json.dumps(collection)};
                    labelTextarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    labelTextarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    labelTextarea.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    return "SET";
                }}
                return "NOT_FOUND";
            }})();
            """
            self.chrome.execute_javascript(w_idx, t_idx, js_set_labels, settle_seconds=0.5)
            
        # 5. Convert markdown to HTML with base64 images
        logger.info("Converting Markdown content to HTML and encoding local images to base64...")
        html_content = self.convert_to_html_with_base64_images(content, payload_dir)
        
        # 6. Ensure HTML view
        logger.info("Ensuring editor is in HTML view...")
        if not self.ensure_html_view(w_idx, t_idx):
            raise SystemExit("Failed to switch to HTML view.")
            
        # 7. Focus CodeMirror and Paste
        logger.info("Focusing CodeMirror...")
        js_focus = """
        (function() {
            const cmEl = document.querySelector('.CodeMirror');
            if (cmEl) {
                const textarea = cmEl.querySelector('textarea');
                if (textarea) {
                    textarea.focus();
                    return "FOCUSED";
                }
            }
            return "FAILED";
        })();
        """
        focus_res = self.chrome.execute_javascript(w_idx, t_idx, js_focus, settle_seconds=0.5)
        if focus_res != "FOCUSED":
            raise SystemExit("Failed to focus CodeMirror HTML editor.")
            
        logger.info("Clearing existing content...")
        self.chrome.run_in_chrome_process('''
            keystroke "a" using {command down}
            delay 0.1
            key code 51 -- Delete key
            delay 0.5
        ''')
        
        logger.info("Pasting final HTML content...")
        p_pbcopy = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        p_pbcopy.communicate(html_content.encode('utf-8'))
        
        self.chrome.run_in_chrome_process('''
            keystroke "v" using {command down}
        ''')
        time.sleep(2.0)
        
        # 8. Switch back to Compose view for user visual check
        logger.info("Switching back to Compose view...")
        self.ensure_compose_view(w_idx, t_idx)
        time.sleep(2.0)
        
        # 9. Click Save to persist draft
        logger.info("Saving draft...")
        js_click_save = """
        (function() {
            const saveBtn = Array.from(document.querySelectorAll('button, div[role="button"]'))
                .find(b => b.getAttribute('aria-label') === 'Save' || b.innerText.trim().toLowerCase() === 'save');
            if (saveBtn) {
                saveBtn.click();
                return "CLICKED";
            }
            return "NOT_FOUND";
        })();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_click_save, settle_seconds=2.0)
        
        # 10. Publish if not dry-run
        if dry_run:
            logger.info("Dry-run mode: skipping final publish step. Post saved as draft.")
            return
            
        logger.info("Publishing post...")
        js_click_publish = """
        (function() {
            const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
            const publishBtn = btns.find(b => b.getAttribute('aria-label') === 'Publish' || b.innerText.trim().toLowerCase().includes('publish') || b.innerText.trim().includes('发布'));
            if (publishBtn) {
                publishBtn.click();
                return "CLICKED";
            }
            return "NOT_FOUND";
        })();
        """
        publish_res = self.chrome.execute_javascript(w_idx, t_idx, js_click_publish, settle_seconds=1.5)
        if publish_res == "CLICKED":
            logger.info("Confirming publication...")
            js_confirm_publish = """
            (function() {
                const allDialogBtns = Array.from(document.querySelectorAll('div[role="dialog"] button, div[role="dialog"] div[role="button"], div[role="alertdialog"] button, div[role="alertdialog"] div[role="button"]'));
                const confirmBtn = allDialogBtns.find(b => b.innerText.toUpperCase() === 'CONFIRM' || b.innerText === '确定' || b.innerText === '确认');
                if (confirmBtn) {
                    confirmBtn.click();
                    return "CONFIRMED";
                }
                return "CONFIRM_NOT_FOUND";
            })();
            """
            confirm_res = self.chrome.execute_javascript(w_idx, t_idx, js_confirm_publish, settle_seconds=2.0)
            logger.info(f"Publish result: {confirm_res}")
        else:
            logger.warning("Could not find Publish button in editor.")
