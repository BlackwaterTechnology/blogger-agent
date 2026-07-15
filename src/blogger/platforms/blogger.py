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
        # Preprocess math formulas in content first (renders block formulas to base64 images)
        from ..core.markdown_parser import preprocess_math
        content = preprocess_math(content, payload_dir)

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
        js_switch = """
        (async function() {
            const cms = Array.from(document.querySelectorAll('.CodeMirror'));
            const cmEl = cms.find(cm => cm.offsetWidth > 0 && cm.offsetHeight > 0);
            if (cmEl) {
                return "ALREADY_HTML";
            }
            
            const toggleBtns = Array.from(document.querySelectorAll('div[aria-label="Toggle view"]'));
            const toggleBtn = toggleBtns.find(b => b.offsetWidth > 0 && b.offsetHeight > 0);
            if (!toggleBtn) return "TOGGLE_BTN_NOT_FOUND";
            
            const clickTarget = toggleBtn.querySelector('[jsname="LgbsSe"]') || toggleBtn;
            clickTarget.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
            clickTarget.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
            clickTarget.click();
            
            let htmlOption = null;
            for (let i = 0; i < 20; i++) {
                await new Promise(r => setTimeout(r, 100));
                const options = Array.from(document.querySelectorAll('div[role="option"]'));
                htmlOption = options.find(o => 
                    (o.innerText.includes('HTML view') || o.innerText.includes('HTML 视图')) && 
                    o.offsetWidth > 0 && 
                    o.offsetHeight > 0
                );
                if (htmlOption) break;
            }
            
            if (!htmlOption) return "HTML_OPTION_NOT_FOUND";
            htmlOption.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
            htmlOption.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
            htmlOption.click();
            
            for (let i = 0; i < 50; i++) {
                await new Promise(r => setTimeout(r, 100));
                const cms = Array.from(document.querySelectorAll('.CodeMirror'));
                const cm = cms.find(c => c.offsetWidth > 0 && c.offsetHeight > 0);
                if (cm) {
                    return "SWITCHED_TO_HTML";
                }
            }
            return "SWITCH_FAILED";
        })();
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_switch, settle_seconds=1.0)
        logger.info(f"HTML view switch status: {res}")
        return res in ("ALREADY_HTML", "SWITCHED_TO_HTML")

    def ensure_compose_view(self, w_idx: int, t_idx: str) -> bool:
        js_switch = """
        (async function() {
            const iframes = Array.from(document.querySelectorAll('iframe.editable'));
            const iframe = iframes.find(f => f.offsetWidth > 0 && f.offsetHeight > 0);
            if (iframe) {
                return "ALREADY_COMPOSE";
            }
            
            const toggleBtns = Array.from(document.querySelectorAll('div[aria-label="Toggle view"]'));
            const toggleBtn = toggleBtns.find(b => b.offsetWidth > 0 && b.offsetHeight > 0);
            if (!toggleBtn) return "TOGGLE_BTN_NOT_FOUND";
            
            // Focus Title input to blur CodeMirror HTML editor before clicking Toggle View
            const titleInput = document.querySelector('input[aria-label="Title"]');
            if (titleInput) {
                titleInput.focus();
                await new Promise(r => setTimeout(r, 100));
            }
            
            const clickTarget = toggleBtn.querySelector('[jsname="LgbsSe"]') || toggleBtn;
            clickTarget.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
            clickTarget.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
            clickTarget.click();
            
            let composeOption = null;
            for (let i = 0; i < 20; i++) {
                await new Promise(r => setTimeout(r, 100));
                const options = Array.from(document.querySelectorAll('div[role="option"]'));
                composeOption = options.find(o => 
                    (o.innerText.includes('Compose view') || o.innerText.includes('撰写视图')) && 
                    o.offsetWidth > 0 && 
                    o.offsetHeight > 0
                );
                if (composeOption) break;
            }
            
            if (!composeOption) return "COMPOSE_OPTION_NOT_FOUND";
            composeOption.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
            composeOption.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
            composeOption.click();
            
            for (let i = 0; i < 50; i++) {
                await new Promise(r => setTimeout(r, 100));
                const iframes = Array.from(document.querySelectorAll('iframe.editable'));
                const iframeEl = iframes.find(f => f.offsetWidth > 0 && f.offsetHeight > 0);
                if (iframeEl) {
                    return "SWITCHED_TO_COMPOSE";
                }
            }
            return "SWITCH_FAILED";
        })();
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_switch, settle_seconds=1.0)
        logger.info(f"Compose view switch status: {res}")
        return res in ("ALREADY_COMPOSE", "SWITCHED_TO_COMPOSE")

    def inject_cover_into_content(self, content: str, cover_filename: str) -> str:
        if cover_filename in content:
            logger.info(f"Blogger platform: cover image {cover_filename} is already present in the article body. Skipping injection.")
            return content

        lines = content.splitlines()
        in_code_block = False
        first_heading_idx = -1
        has_image_before_heading = False
        
        img_pattern = re.compile(r'!\[.*?\]\(.*?\)')
        html_img_pattern = re.compile(r'<img\s+[^>]*>')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('```') or stripped.startswith('~~~'):
                in_code_block = not in_code_block
                continue
                
            if in_code_block:
                continue
                
            if stripped.startswith('#') and re.match(r'^#{1,6}\s+', stripped):
                first_heading_idx = i
                break
                
            if img_pattern.search(line) or html_img_pattern.search(line):
                has_image_before_heading = True
                
        cover_md = f"![Cover]({cover_filename})"
        
        if has_image_before_heading or first_heading_idx == -1:
            return cover_md + "\n\n" + content
        else:
            before_heading = lines[:first_heading_idx]
            after_heading = lines[first_heading_idx:]
            
            while before_heading and not before_heading[-1].strip():
                before_heading.pop()
                
            before_str = "\n".join(before_heading).strip()
            if before_str:
                return before_str + "\n\n" + cover_md + "\n\n" + "\n".join(after_heading)
            else:
                return cover_md + "\n\n" + "\n".join(after_heading)

    def publish(self, article_data: dict, *, dry_run: bool = False) -> None:
        title = article_data.get("title", "")
        content = article_data.get("content", "")
        collection = article_data.get("collection", "")
        
        # Resolve payload directory
        payload_path = article_data.get("payload_path")
        if payload_path:
            payload_path = Path(payload_path)
            payload_dir = payload_path.parent if payload_path.is_file() else payload_path
        else:
            payload_dir = Path.cwd()

        # Check if cover image exists and needs to be injected into content
        cover_path = article_data.get("cover_path")
        if cover_path:
            cover_path = Path(cover_path)
            if not cover_path.exists() and not cover_path.is_absolute():
                cover_path = payload_dir / cover_path
            
            if cover_path.exists():
                cover_filename = cover_path.name
                logger.info(f"Blogger platform: injecting cover image {cover_filename} into content body...")
                content = self.inject_cover_into_content(content, cover_filename)
            
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
            
            logger.info("Editor loaded. Waiting 3.0 seconds for framework to settle...")
            time.sleep(3.0)
        else:
            # Already on the editor page. Make sure it is fully loaded before continuing!
            logger.info("Already on the editor page. Waiting for editor to load...")
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
            
            logger.info("Editor loaded. Waiting 3.0 seconds for framework to settle...")
            time.sleep(3.0)
                
        # (Title and Labels setting moved to Compose view stage right before publishing)
            
        # 5. Convert markdown to HTML with base64 images
        logger.info("Converting Markdown content to HTML and encoding local images to base64 (with formulas)...")
        html_content = self.convert_to_html_with_base64_images(content, payload_dir)
        
        # 6. Ensure HTML view
        logger.info("Ensuring editor is in HTML view...")
        if not self.ensure_html_view(w_idx, t_idx):
            raise SystemExit("Failed to switch to HTML view.")
            
        # 7. Set HTML content directly via CodeMirror JS API
        logger.info("Setting HTML content directly via CodeMirror API...")
        js_set_content = """
        (function() {
            const cms = Array.from(document.querySelectorAll('.CodeMirror'));
            const cmEl = cms.find(cm => cm.offsetWidth > 0 && cm.offsetHeight > 0);
            if (cmEl && cmEl.CodeMirror) {
                cmEl.CodeMirror.setValue(""" + json.dumps(html_content) + """);
                return "SET_OK";
            }
            return "CM_NOT_FOUND";
        })();
        """
        set_content_res = self.chrome.execute_javascript(w_idx, t_idx, js_set_content, settle_seconds=1.0)
        if set_content_res != "SET_OK":
            raise SystemExit(f"Failed to set HTML content: {set_content_res}")
        logger.info("HTML content successfully set.")
        time.sleep(2.0)
        
        # 8. Switch back to Compose view for user visual check
        logger.info("Switching back to Compose view...")
        self.ensure_compose_view(w_idx, t_idx)
        time.sleep(3.0)
        
        # 8b. Set Title and Labels here, right before publishing, so that GWT view switches
        # or auto-saves never have a chance to wipe them.
        logger.info(f"Setting title: {title}")
        js_focus_title = """
        (function() {
            const inputs = Array.from(document.querySelectorAll('input[aria-label="Title"]'));
            const titleInput = inputs.find(el => el.offsetWidth > 0 && el.offsetHeight > 0);
            if (titleInput) {
                titleInput.select();
                titleInput.focus();
                titleInput.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                titleInput.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                titleInput.click();
                return "FOCUSED";
            }
            return "NOT_FOUND";
        })();
        """
        focus_res = self.chrome.execute_javascript(w_idx, t_idx, js_focus_title, settle_seconds=0.5)
        if focus_res != "FOCUSED":
            raise SystemExit(f"Failed to focus title input: {focus_res}")
            
        subprocess.run(["pbcopy"], input=title.encode('utf-8'), check=True)
        self.chrome.run_in_chrome_process('''
            keystroke "a" using {command down}
            delay 0.1
            keystroke "v" using {command down}
            delay 0.2
        ''')
            
        # Verify title is set
        js_verify_title = """
        (function() {
            const inputs = Array.from(document.querySelectorAll('input[aria-label="Title"]'));
            const titleInput = inputs.find(el => el.offsetWidth > 0 && el.offsetHeight > 0);
            return titleInput ? titleInput.value : "";
        })();
        """
        actual_title = self.chrome.execute_javascript(w_idx, t_idx, js_verify_title)
        if actual_title != title:
            raise SystemExit(f"Title verification failed! Expected: {title!r}, Got: {actual_title!r}")
        logger.info("Title successfully set and verified.")
        
        if collection:
            logger.info(f"Setting labels: {collection}")
            js_focus_labels = """
            (function() {
                const textareas = Array.from(document.querySelectorAll('textarea[aria-label="Separate labels by commas"]'));
                const labelTextarea = textareas.find(el => el.offsetWidth > 0 && el.offsetHeight > 0);
                if (labelTextarea) {
                    labelTextarea.select();
                    labelTextarea.focus();
                    labelTextarea.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    labelTextarea.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                    labelTextarea.click();
                    return "FOCUSED";
                }
                return "NOT_FOUND";
            })();
            """
            focus_labels_res = self.chrome.execute_javascript(w_idx, t_idx, js_focus_labels, settle_seconds=0.5)
            if focus_labels_res != "FOCUSED":
                raise SystemExit(f"Failed to focus labels input: {focus_labels_res}")
                
            subprocess.run(["pbcopy"], input=collection.encode('utf-8'), check=True)
            self.chrome.run_in_chrome_process('''
                keystroke "a" using {command down}
                delay 0.1
                keystroke "v" using {command down}
                delay 0.2
            ''')
                
            # Verify labels are set
            js_verify_labels = """
            (function() {
                const textareas = Array.from(document.querySelectorAll('textarea[aria-label="Separate labels by commas"]'));
                const labelTextarea = textareas.find(el => el.offsetWidth > 0 && el.offsetHeight > 0);
                return labelTextarea ? labelTextarea.value : "";
            })();
            """
            actual_labels = self.chrome.execute_javascript(w_idx, t_idx, js_verify_labels)
            if actual_labels != collection:
                raise SystemExit(f"Labels verification failed! Expected: {collection!r}, Got: {actual_labels!r}")
            logger.info("Labels successfully set and verified.")
        
        # 9. Save or Publish
        if dry_run:
            logger.info("Saving draft...")
            js_click_save = """
            (function() {
                const saveBtn = Array.from(document.querySelectorAll('button, div[role="button"]'))
                    .find(b => (b.getAttribute('aria-label') === 'Save' || b.innerText.trim().toLowerCase() === 'save') && b.offsetWidth > 0 && b.offsetHeight > 0);
                if (saveBtn) {
                    saveBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    saveBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                    saveBtn.click();
                    return "CLICKED";
                }
                return "NOT_FOUND";
            })();
            """
            self.chrome.execute_javascript(w_idx, t_idx, js_click_save, settle_seconds=2.0)
            logger.info("Dry-run mode: skipping final publish step. Post saved as draft.")
            return
            
        logger.info("Publishing post...")
        js_click_publish = """
        (function() {
            const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
            const publishBtn = btns.find(b => 
                (b.getAttribute('aria-label') === 'Publish' || 
                 b.innerText.trim().toLowerCase().includes('publish') || 
                 b.innerText.trim().includes('发布')) &&
                b.offsetWidth > 0 && b.offsetHeight > 0
            );
            if (publishBtn) {
                publishBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                publishBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                publishBtn.click();
                return "CLICKED";
            }
            return "NOT_FOUND";
        })();
        """
        publish_res = self.chrome.execute_javascript(w_idx, t_idx, js_click_publish, settle_seconds=2.0)
        if publish_res == "CLICKED":
            logger.info("Confirming publication...")
            js_confirm_publish = """
            (function() {
                const allDialogBtns = Array.from(document.querySelectorAll('div[role="dialog"] button, div[role="dialog"] div[role="button"], div[role="alertdialog"] button, div[role="alertdialog"] div[role="button"]'));
                const confirmBtn = allDialogBtns.find(b => 
                    (b.innerText.toUpperCase() === 'CONFIRM' || b.innerText === '确定' || b.innerText === '确认') &&
                    b.offsetWidth > 0 && b.offsetHeight > 0
                );
                if (confirmBtn) {
                    confirmBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    confirmBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
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
