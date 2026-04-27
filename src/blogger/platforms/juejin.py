import time
import json
import subprocess
from loguru import logger
from ..core.jxa_chrome import JxaChromeController

class JuejinPublisher:
    def __init__(self):
        self.chrome = JxaChromeController()

    def run_ui_state_machine(self, name, w_idx, t_idx, js_code, max_steps=10, delay=1.5):
        logger.info(f"Starting UI State Machine: {name}")
        for step in range(1, max_steps + 1):
            res_str = self.chrome.execute_javascript(w_idx, t_idx, js_code)
            try:
                res = json.loads(res_str)
            except Exception as e:
                logger.warning(f"[{name}] Failed to parse JS result: {res_str!r} | Error: {e}")
                time.sleep(delay)
                continue
                
            state = res.get("state", {})
            action = res.get("action", "")
            is_done = res.get("is_done", False)
            
            logger.info(f"[{name}] Step {step} | State: {state} | Action: {action}")
            
            if is_done:
                logger.info(f"[{name}] Completed successfully.")
                return True
                
            if "Error" in action or action == "No action available":
                logger.warning(f"[{name}] Stopped due to: {action}")
                return False
                
            time.sleep(delay)
        logger.warning(f"[{name}] Failed to complete within {max_steps} steps.")
        return False

    def publish(self, article_data: dict) -> None:
        title = article_data.get("title", "")
        content = article_data.get("content", "")
        desc = article_data.get("desc", "")
        cover_path = article_data.get("cover_path")
        illustration_path = article_data.get("illustration_path")

        # 1. Find Juejin Tab
        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://juejin.cn"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(f"Juejin tab not found in Chrome: {e}")
            
        logger.info(f"Found Juejin tab: {url}")
        
        # 2. Navigate to Draft Editor
        if "editor" not in url:
            logger.info("Not currently on the editor page. Navigating to drafts...")
            try:
                self.chrome.set_tab_url(w_idx, t_idx, "https://juejin.cn/editor/drafts/new", settle_seconds=3.0)
            except Exception as e:
                logger.warning(f"Failed to navigate: {e}")
                
            logger.info("Waiting 5 seconds for editor to fully load...")
            time.sleep(5)
            
        # 3. Inject Content via PBCOPY and Cmd+V
        # First, inject the Title via JS
        js_inject_title = f"""
        (function() {{
            try {{
                const title = {json.dumps(title)};
                let action = [];
                
                // Set Title
                const titleInput = document.querySelector('.title-input');
                if (titleInput && titleInput.value !== title) {{
                    titleInput.value = title;
                    titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    action.push("Set Title");
                }}
                
                // Focus the CodeMirror textarea to prepare for Cmd+V
                const textarea = document.querySelector('.CodeMirror textarea');
                if (textarea) {{
                    textarea.focus();
                    action.push("Focused CodeMirror textarea");
                }} else {{
                    const bytemdEditor = document.querySelector('.bytemd-editor');
                    if (bytemdEditor) bytemdEditor.focus();
                }}
                
                return JSON.stringify({{ action: action.join(", "), is_done: true }});
            }} catch (err) {{
                return JSON.stringify({{ error: "Error in JS: " + err.message }});
            }}
        }})();
        """
        
        logger.info("Injecting title and focusing editor...")
        try:
            inject_res = self.chrome.execute_javascript(w_idx, t_idx, js_inject_title, settle_seconds=1.0)
            logger.info(f"Injection result: {inject_res}")
        except Exception as e:
            logger.warning(f"JS injection failed: {e}")
            
        # Clear existing content
        logger.info("Clearing existing content in editor...")
        try:
            applescript_clear = '''
            tell application "System Events"
                tell process "Google Chrome"
                    set frontmost to true
                    delay 0.5
                    keystroke "a" using {command down}
                    delay 0.1
                    key code 51 -- Delete key
                    delay 0.5
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", applescript_clear], check=True)
        except Exception as e:
            logger.warning(f"Failed to clear editor: {e}")
            
        # 1. Upload the illustration first if provided to get the Juejin CDN URL
        if illustration_path:
            logger.info(f"Found illustration image: {illustration_path}. Extracting CDN link...")
            try:
                # Copy illustration to clipboard
                applescript_copy_illus = f'set the clipboard to (read (POSIX file "{illustration_path.absolute()}") as TIFF picture)'
                subprocess.run(["osascript", "-e", applescript_copy_illus], check=True)
                
                # Paste into the empty editor
                applescript_paste_illus = '''
                tell application "System Events"
                    tell process "Google Chrome"
                        set frontmost to true
                        delay 0.5
                        keystroke "v" using {command down}
                    end tell
                end tell
                '''
                subprocess.run(["osascript", "-e", applescript_paste_illus], check=True)
                
                # Poll for the uploaded URL via JS
                logger.info("Waiting for Juejin to upload the illustration...")
                js_extract_img = """
                (function() {
                    const el = document.querySelector('.bytemd-editor .CodeMirror-code');
                    if (!el) return "";
                    const text = el.innerText;
                    if (text.includes('Uploading')) return "UPLOADING";
                    const match = text.match(/!\\[.*?\\]\\((https:\\/\\/.*?)\\)/);
                    if (match) return match[0];
                    return "";
                })();
                """
                illustration_markdown = ""
                for _ in range(15):  # Wait up to 15 seconds
                    res_str = self.chrome.execute_javascript(w_idx, t_idx, js_extract_img, settle_seconds=1.0)
                    if res_str and res_str != "UPLOADING" and res_str.startswith("!["):
                        illustration_markdown = res_str
                        break
                    time.sleep(1.0)
                    
                if illustration_markdown:
                    logger.info(f"Extracted illustration markdown: {illustration_markdown}")
                    # Insert before the first heading in the markdown text
                    lines = content.split('\n')
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('#'):
                            insert_idx = i
                            break
                    
                    if insert_idx > 0:
                        content = "\n".join(lines[:insert_idx]) + f"\n\n{illustration_markdown}\n\n" + "\n".join(lines[insert_idx:])
                    else:
                        # Fallback: put at the very beginning if no heading is found, 
                        # or if the first line is already a heading.
                        content = f"{illustration_markdown}\n\n{content}"
                else:
                    logger.warning("Failed to extract uploaded illustration link from editor.")
                    
            except Exception as e:
                logger.warning(f"Failed to process illustration: {e}")
                
        # 2. Clear editor again before pasting the final content
        logger.info("Clearing editor for final content...")
        try:
            applescript_clear = '''
            tell application "System Events"
                tell process "Google Chrome"
                    set frontmost to true
                    delay 0.5
                    keystroke "a" using {command down}
                    delay 0.1
                    key code 51 -- Delete key
                    delay 0.5
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", applescript_clear], check=True)
        except Exception as e:
            logger.warning(f"Failed to clear editor: {e}")

        # 3. Paste the final combined content using Cmd+V
        logger.info("Pasting final content into Juejin editor...")
        try:
            p_pbcopy = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p_pbcopy.communicate(content.encode('utf-8'))
            
            applescript_paste = '''
            tell application "System Events"
                tell process "Google Chrome"
                    set frontmost to true
                    delay 0.5
                    keystroke "v" using {command down}
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", applescript_paste], check=True)
            time.sleep(2.0)
        except Exception as e:
            logger.warning(f"Failed to paste content: {e}")

        # 4. Open Publish Dialog
        js_open_publish = """
        (function() {
            try {
                function clickReactElement(el) {
                    if (!el) return false;
                    const key = Object.keys(el).find(k => k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$'));
                    if (key && el[key] && el[key].onClick) {
                        el[key].onClick({
                            preventDefault: () => {},
                            stopPropagation: () => {},
                            nativeEvent: new MouseEvent('click', {bubbles: true, cancelable: true}),
                            isDefaultPrevented: () => false,
                            isPropagationStopped: () => false,
                            target: el,
                            currentTarget: el
                        });
                        return true;
                    }
                    el.click();
                    return true;
                }

                const btns = Array.from(document.querySelectorAll('button'));
                const publishBtn = btns.find(b => b.innerText && b.innerText.includes('发布'));
                if (publishBtn) {
                    clickReactElement(publishBtn);
                    return JSON.stringify({ action: "Clicked Publish button", is_done: true });
                }
                return JSON.stringify({ action: "Publish button not found", is_done: false });
            } catch (err) {
                return JSON.stringify({ error: err.message, is_done: false });
            }
        })();
        """
        logger.info("Clicking Publish to open dialog...")
        self.run_ui_state_machine("Open Publish Dialog", w_idx, t_idx, js_open_publish, max_steps=5)
        
        # 5. Handle Cover Image Upload using macOS File Dialog
        if cover_path:
            logger.info(f"Found cover image: {cover_path}. Attempting to upload...")
            try:
                js_click_cover = """
                (function() {
                    try {
                        const fileInput = document.querySelector('.byte-upload input[type="file"]') || document.querySelector('input[type="file"]');
                        if (fileInput) {
                            fileInput.click();
                            return "Clicked file input directly";
                        }
                        return "Cover upload area not found";
                    } catch (err) {
                        return err.message;
                    }
                })();
                """
                
                # Poll until the file input is found and clicked (max 5 tries)
                clicked = False
                for _ in range(5):
                    res = self.chrome.execute_javascript(w_idx, t_idx, js_click_cover, settle_seconds=1.0)
                    if "Clicked" in res:
                        clicked = True
                        break
                    time.sleep(1)
                
                if clicked:
                    applescript_file_dialog = f'''
                    set the clipboard to "{cover_path.absolute()}"
                    tell application "System Events"
                        tell process "Google Chrome"
                            set frontmost to true
                            delay 2.0
                            keystroke "G" using {{command down, shift down}}
                            delay 2.0
                            keystroke "v" using {{command down}}
                            delay 1.5
                            key code 36 -- Return key
                            delay 1.5
                            key code 36 -- Return key
                        end tell
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", applescript_file_dialog], check=True)
                    logger.info("Successfully initiated cover image upload via file dialog.")
                    time.sleep(4.0)
                else:
                    logger.warning(f"Skipping cover upload, area not clicked: {res}")
            except Exception as e:
                logger.warning(f"Failed to upload cover image: {e}")

        # 6. Fill Publish Dialog Data (Category, Tags, Desc)
        # Note: In an actual robust implementation, you would map `article_data['category']` 
        # to the actual DOM elements. Here we use a generic state machine to select the first 
        # category and first tag if not specified, and fill the description.
        js_publish_dialog = f"""
        (function() {{
            try {{
                const desc = {json.dumps(desc)};
                let state = {{}};
                let action = [];
                
                // Fill Abstract/Summary
                const textareas = Array.from(document.querySelectorAll('.byte-input__textarea, textarea'));
                const summaryInput = textareas.find(t => t.placeholder && t.placeholder.includes('摘要')) || textareas[0];
                if (summaryInput && summaryInput.value !== desc && desc) {{
                    summaryInput.value = desc;
                    summaryInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    action.push("Filled summary");
                }}
                
                // Select category (后端 by default if none selected)
                const categoryItems = Array.from(document.querySelectorAll('.category-list .item'));
                const hasSelectedCategory = categoryItems.some(i => i.classList.contains('active'));
                if (!hasSelectedCategory && categoryItems.length > 0) {{
                    const backendCat = categoryItems.find(c => c.innerText.includes('后端'));
                    if (backendCat) backendCat.click();
                    else categoryItems[0].click();
                    action.push("Selected default category");
                }}
                
                return JSON.stringify({{state: state, action: action.join(", "), is_done: true}});
            }} catch (err) {{
                return JSON.stringify({{ error: err.message, is_done: false }});
            }}
        }})();
        """
        self.run_ui_state_machine("Publish Dialog Setup", w_idx, t_idx, js_publish_dialog, max_steps=5)

        logger.info("Juejin article is ready in draft/publish dialog. Awaiting manual confirmation to submit.")
