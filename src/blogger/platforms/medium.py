import time
import json
import re
import subprocess
from pathlib import Path
from loguru import logger
import markdown
from ..core.cdp_chrome import CdpChromeController

class MediumPublisher:
    def __init__(self):
        self.chrome = CdpChromeController()

    def copy_to_clipboard(self, text: str):
        subprocess.run(["pbcopy"], input=text.encode('utf-8'), check=True)

    def copy_html_to_clipboard(self, html_str: str):
        hex_html = html_str.encode('utf-8').hex()
        as_code = f'set the clipboard to «data HTML{hex_html}»'
        process = subprocess.Popen(["osascript"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=as_code.encode('utf-8'))
        if process.returncode != 0:
            raise RuntimeError(f"osascript copy HTML failed: {stderr.decode('utf-8')}")

    def native_click(self, w_idx: int, t_idx: str, get_element_js: str) -> str:
        """Finds an element using the provided JS expression, gets its coordinates,
        and dispatches a native mouse click via CDP. Falls back to programmatic click."""
        js_get_coords = f"""
        (function() {{
            const el = ({get_element_js});
            if (!el) return "NOT_FOUND";
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return "NOT_VISIBLE";
            return JSON.stringify({{
                x: Math.round(rect.left + rect.width / 2),
                y: Math.round(rect.top + rect.height / 2)
            }});
        }})();
        """
        coords_str = self.chrome.execute_javascript(w_idx, t_idx, js_get_coords, settle_seconds=0.2)
        if coords_str and coords_str not in ("NOT_FOUND", "NOT_VISIBLE"):
            try:
                coords = json.loads(coords_str)
                x, y = coords["x"], coords["y"]
                logger.info(f"Clicking element natively at coordinates ({x}, {y})")
                self.chrome._call_on(t_idx, "Input.dispatchMouseEvent", {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 1
                })
                time.sleep(0.1)
                self.chrome._call_on(t_idx, "Input.dispatchMouseEvent", {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 1
                })
                return "CLICKED_NATIVE"
            except Exception as e:
                logger.warning(f"Native click failed, attempting programmatic click fallback: {e}")
        
        # Fallback to programmatic click
        js_fallback = f"""
        (function() {{
            const el = ({get_element_js});
            if (!el) return "NOT_FOUND";
            el.click();
            return "CLICKED_PROGRAMMATIC";
        }})();
        """
        return self.chrome.execute_javascript(w_idx, t_idx, js_fallback, settle_seconds=0.5)

    def inject_cover_into_content(self, content: str, cover_filename: str) -> str:
        if cover_filename in content:
            logger.info(f"Medium platform: cover image {cover_filename} is already present in the article body. Skipping injection.")
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
        desc = article_data.get("desc", "")
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
        cover_injected = False
        if cover_path:
            cover_path = Path(cover_path)
            if not cover_path.exists() and not cover_path.is_absolute():
                cover_path = payload_dir / cover_path
            
            if cover_path.exists():
                cover_filename = cover_path.name
                logger.info(f"Medium platform: injecting cover image {cover_filename} into content body...")
                content = self.inject_cover_into_content(content, cover_filename)
                cover_injected = True

        local_images = list(article_data.get("local_images", []))
        if cover_injected and cover_path and cover_path not in local_images:
            local_images.insert(0, cover_path)

        # 1. Find Medium tab (any page on medium.com)
        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://medium.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(
                f"Medium tab not found in Chrome. Open Medium (medium.com) "
                f"in a logged-in tab and retry. Detail: {e}"
            )
            
        logger.info(f"Found Medium tab: {url}")
        
        # 2. Navigate to new story to start a fresh draft
        logger.info("Navigating to new story page to create a fresh draft...")
        self.chrome.set_tab_url(w_idx, t_idx, "https://medium.com/new-story", settle_seconds=4.0)
            
        logger.info("Waiting for editor to fully load...")
        js_check_loaded = """
        (function() {
            if (document.title.includes("Just a moment...") || document.querySelector('#challenge-running') || document.querySelector('#turnstile-wrapper')) {
                return "CLOUDFLARE";
            }
            const editor = document.querySelector('.postArticle-content');
            const titleInput = document.querySelector('h3.graf--title');
            if (editor && titleInput) {
                return "LOADED";
            }
            return "LOADING";
        })();
        """
        editor_loaded = False
        cf_logged = False
        for i in range(120): # up to 60 seconds
            try:
                res = self.chrome.execute_javascript(w_idx, t_idx, js_check_loaded, settle_seconds=0.5)
                if res == "LOADED":
                    editor_loaded = True
                    break
                elif res == "CLOUDFLARE":
                    if not cf_logged:
                        logger.warning("Cloudflare Turnstile challenge detected! Please solve the challenge in the Chrome window to proceed...")
                        try:
                            self.chrome.activate()
                        except Exception:
                            pass
                        cf_logged = True
            except Exception:
                pass
            time.sleep(0.5)
            
        if not editor_loaded:
            raise SystemExit("Medium editor failed to load in time. Please solve the Cloudflare Turnstile challenge in Chrome or check your connection.")

        # 3. Handle local images upload first to extract CDN links
        if local_images:
            logger.info(f"Found {len(local_images)} local images. Uploading to Medium CDN...")
            
            for img_path in local_images:
                if not img_path.exists() and not img_path.is_absolute():
                    img_path = payload_dir / img_path
                
                if not img_path.exists():
                    logger.warning(f"Image not found: {img_path}")
                    continue

                # 3a. Clear editor to start fresh for this image upload
                self.chrome.run_in_chrome_process('''
                    keystroke "a" using {command down}
                    delay 0.1
                    keystroke "a" using {command down}
                    delay 0.1
                    key code 51 -- Delete key
                    delay 0.3
                ''')

                # 3b. Focus Title
                js_focus_title = """
                (function() {
                    const titleEl = document.querySelector('h3.graf--title');
                    if (titleEl) {
                        titleEl.focus();
                        return "TITLE_FOCUSED";
                    }
                    return "NO_TITLE_EL";
                })();
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_focus_title, settle_seconds=0.2)

                # 3c. Press Enter to create body block
                self.chrome.run_in_chrome_process('''
                    key code 36 -- Enter key
                    delay 0.3
                ''')

                # 3d. Focus body block
                js_focus_body = """
                (function() {
                    const bodyEl = document.querySelector('.postArticle-content p.graf--p');
                    if (bodyEl) {
                        bodyEl.focus();
                        return "BODY_FOCUSED";
                    }
                    return "NO_BODY_EL";
                })();
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_focus_body, settle_seconds=0.2)

                try:
                    logger.info(f"Uploading image {img_path.name}...")
                    # Copy image to clipboard as TIFF
                    applescript_copy = f'set the clipboard to (read (POSIX file "{img_path.absolute()}") as TIFF picture)'
                    subprocess.run(["osascript", "-e", applescript_copy], check=True)

                    # Paste (pasted inside the body paragraph block)
                    self.chrome.run_in_chrome_process('''
                        keystroke "v" using {command down}
                    ''')

                    # Poll for CDN URL
                    js_get_image_url = """
                    (function() {
                        const img = document.querySelector('.postArticle-content img.graf-image');
                        if (!img) return "NO_IMG_YET";
                        const src = img.src;
                        if (src.startsWith('https://cdn-images-1.medium.com')) {
                            return src;
                        }
                        return "LOADING";
                    })();
                    """
                    cdn_url = ""
                    for i in range(15):  # Wait up to 15 seconds
                        res_url = self.chrome.execute_javascript(w_idx, t_idx, js_get_image_url, settle_seconds=1.0)
                        if res_url.startswith("https://cdn-images-1.medium.com"):
                            cdn_url = res_url
                            break
                        time.sleep(1.0)

                    if cdn_url:
                        logger.info(f"Extracted Medium CDN URL for {img_path.name}: {cdn_url}")
                        # Replace in markdown
                        local_img_name = img_path.name
                        pattern = rf'!\[(.*?)\]\(.*?{re.escape(local_img_name)}\)'
                        content = re.sub(pattern, f'![\\1]({cdn_url})', content)
                    else:
                        logger.warning(f"Failed to get CDN link for image: {img_path.name}")

                except Exception as e:
                    logger.warning(f"Failed to process image {img_path.name}: {e}")

            # 3e. Clear editor completely after all images are uploaded
            logger.info("Clearing editor after all uploads...")
            self.chrome.run_in_chrome_process('''
                keystroke "a" using {command down}
                delay 0.1
                keystroke "a" using {command down}
                delay 0.1
                key code 51 -- Delete key
                delay 0.3
            ''')

        # 5. Convert Markdown to HTML
        logger.info("Converting Markdown content to HTML (with math formulas)...")
        from ..core.markdown_parser import preprocess_math
        preprocessed_content = preprocess_math(content, payload_dir)
        html_content = markdown.markdown(preprocessed_content, extensions=['fenced_code', 'tables', 'sane_lists'])
        # Strip horizontal rules (<hr>) as requested by user
        html_content = re.sub(r'<hr\s*/?>', '', html_content)

        # 6. Paste Title
        logger.info(f"Pasting title: {title}")
        js_focus_title = """
        (function() {
            const titleEl = document.querySelector('h3.graf--title');
            if (titleEl) {
                titleEl.focus();
                const range = document.createRange();
                const sel = window.getSelection();
                range.selectNodeContents(titleEl);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
                return "TITLE_FOCUSED";
            }
            return "TITLE_NOT_FOUND";
        })();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_focus_title, settle_seconds=0.5)
        self.copy_to_clipboard(title)
        self.chrome.run_in_chrome_process('''
            keystroke "v" using {command down}
            delay 0.5
            key code 36 -- Enter key to create and focus body paragraph
            delay 0.5
        ''')

        # 7. Paste Body HTML
        logger.info("Pasting body HTML content...")
        self.copy_html_to_clipboard(html_content)
        self.chrome.run_in_chrome_process('''
            keystroke "v" using {command down}
            delay 1.5
        ''')

        # 8. Trigger Publish Dialog
        logger.info("Opening publish settings menu...")
        js_get_publish_btn = """
        (function() {
            const btn = document.querySelector('.button--publish, .js-publishButton');
            if (!btn || btn.disabled || btn.classList.contains('button--disabledPrimary')) {
                return null;
            }
            return btn;
        })()
        """
        publish_clicked = False
        for _ in range(10):
            res = self.native_click(w_idx, t_idx, js_get_publish_btn)
            logger.info(f"Publish button click attempt: {res}")
            if "CLICKED" in res:
                publish_clicked = True
                break
            time.sleep(1.0)

        if not publish_clicked:
            raise SystemExit("Failed to click Publish button (it might be disabled or not loaded).")

        # Wait for the settings page to settle
        logger.info("Waiting for publishing settings page to settle...")
        time.sleep(3.0)

        # 9. Handle Preview Subtitle/Description
        if desc:
            logger.info(f"Setting preview description: {desc}")
            js_focus_desc = """
            (function() {
                const textarea = document.querySelector('textarea[placeholder="Write a preview subtitle..."]');
                if (textarea) {
                    textarea.focus();
                    textarea.select();
                    return "FOCUSED";
                }
                return "NOT_FOUND";
            })();
            """
            res_desc = self.chrome.execute_javascript(w_idx, t_idx, js_focus_desc, settle_seconds=0.5)
            if res_desc == "FOCUSED":
                self.copy_to_clipboard(desc)
                self.chrome.run_in_chrome_process('''
                    keystroke "a" using {command down}
                    delay 0.1
                    keystroke "v" using {command down}
                    delay 0.5
                ''')

        # 10. Handle Tags/Topics (from collection / tags)
        tags = []
        if collection:
            tags = [t.strip() for t in collection.split(",") if t.strip()]

        if tags:
            logger.info(f"Adding topics/tags: {tags}")
            for tag in tags:
                js_focus_tag_input = """
                (function() {
                    const input = document.querySelector('input[placeholder="Add a topic..."], input[placeholder="Add more topics..."]');
                    if (input) {
                        input.value = "";
                        input.focus();
                        return "FOCUSED";
                    }
                    return "NOT_FOUND";
                })();
                """
                res_tag = self.chrome.execute_javascript(w_idx, t_idx, js_focus_tag_input, settle_seconds=0.5)
                if res_tag == "FOCUSED":
                    self.copy_to_clipboard(tag)
                    self.chrome.run_in_chrome_process('''
                        keystroke "v" using {command down}
                        delay 0.8
                    ''')
                    
                    # Click dropdown selection
                    js_click_dropdown = """
                    (function() {
                        const ul = document.querySelector('ul');
                        if (!ul) return "UL_NOT_FOUND";
                        const btn = ul.querySelector('button');
                        if (!btn) return "BUTTON_NOT_FOUND";
                        const text = btn.innerText;
                        btn.click();
                        return "CLICKED: " + text;
                    })();
                    """
                    click_res = self.chrome.execute_javascript(w_idx, t_idx, js_click_dropdown, settle_seconds=1.0)
                    logger.info(f"Clicked dropdown option for tag '{tag}': {click_res}")

        logger.info("Medium article configuration complete.")

        if dry_run:
            logger.info("Dry-run mode: skipping final submit click. The publishing settings page is left open for manual review.")
            return

        # 11. Final Submit
        logger.info("Submitting article to Medium...")
        js_get_submit_btn = """
        (function() {
            return Array.from(document.querySelectorAll('button')).find(
                b => b.innerText.trim() === 'Publish now' || 
                     b.innerText.trim() === 'Publish' || 
                     b.innerText.trim() === 'Submit'
            );
        })()
        """
        res_submit = self.native_click(w_idx, t_idx, js_get_submit_btn)
        logger.info(f"Publish final result: {res_submit}")
