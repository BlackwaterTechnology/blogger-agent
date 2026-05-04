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
        local_images = article_data.get("local_images", [])

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
                self.chrome.set_tab_url(w_idx, t_idx, "https://juejin.cn/editor/drafts/new", settle_seconds=1.0)
            except Exception as e:
                logger.warning(f"Failed to navigate: {e}")
                
            logger.info("Waiting for editor to fully load...")
            js_check_loaded = """
            (function() {
                const titleInput = document.querySelector('.title-input');
                const editor = document.querySelector('.CodeMirror textarea') || document.querySelector('.bytemd-editor');
                if (titleInput && editor) {
                    return "LOADED";
                }
                return "LOADING";
            })();
            """
            for _ in range(15):
                try:
                    res = self.chrome.execute_javascript(w_idx, t_idx, js_check_loaded, settle_seconds=0.5)
                    if res == "LOADED":
                        break
                except Exception:
                    pass
                time.sleep(1.0)
            
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
        if local_images:
            logger.info(f"Found {len(local_images)} local images. Extracting CDN links...")
            for img_path in local_images:
                try:
                    # Copy illustration to clipboard
                    applescript_copy_illus = f'set the clipboard to (read (POSIX file "{img_path.absolute()}") as TIFF picture)'
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
                    logger.info(f"Waiting for Juejin to upload image {img_path.name}...")
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
                        logger.info(f"Extracted image markdown: {illustration_markdown}")
                        import re
                        local_img_name = img_path.name
                        pattern = rf'!\[.*?\]\(.*?{re.escape(local_img_name)}\)'
                        
                        if re.search(pattern, content):
                            # It's an inline image, replace it
                            content = re.sub(pattern, illustration_markdown, content, count=1)
                        else:
                            # It's from FrontMatter illustration, insert before first heading
                            lines = content.split('\n')
                            insert_idx = 0
                            for i, line in enumerate(lines):
                                if line.strip().startswith('#'):
                                    insert_idx = i
                                    break
                            
                            if insert_idx > 0:
                                content = "\n".join(lines[:insert_idx]) + f"\n\n{illustration_markdown}\n\n" + "\n".join(lines[insert_idx:])
                            else:
                                content = f"{illustration_markdown}\n\n{content}"
                        
                        # CLEAR EDITOR for next image
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
                    else:
                        logger.warning(f"Failed to extract uploaded image link for {img_path.name}.")
                        
                except Exception as e:
                    logger.warning(f"Failed to process image {img_path.name}: {e}")
                
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

        # 6. Fill Publish Dialog Data (Summary, Category)
        logger.info("Setting up Publish Dialog (Summary & Category)...")
        js_publish_dialog_part1 = f"""
        (function() {{
            try {{
                const desc = {json.dumps(desc)};
                let action = [];
                
                function clickReactElement(el) {{
                    if (!el) return false;
                    const key = Object.keys(el).find(k => k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$'));
                    if (key && el[key] && el[key].onClick) {{
                        el[key].onClick({{
                            preventDefault: () => {{}},
                            stopPropagation: () => {{}},
                            nativeEvent: new MouseEvent('click', {{bubbles: true, cancelable: true}}),
                            isDefaultPrevented: () => false,
                            isPropagationStopped: () => false,
                            target: el,
                            currentTarget: el
                        }});
                        return true;
                    }}
                    el.click();
                    return true;
                }}
                
                function setReactInputValue(input, value) {{
                    let lastValue = input.value;
                    input.value = value;
                    let event = new Event('input', {{ bubbles: true }});
                    event.simulated = true;
                    let tracker = input._valueTracker;
                    if (tracker) {{
                        tracker.setValue(lastValue);
                    }}
                    input.dispatchEvent(event);
                }}

                // Fill Abstract/Summary
                const textareas = Array.from(document.querySelectorAll('.byte-input__textarea, textarea'));
                const summaryInput = textareas.find(t => t.placeholder && t.placeholder.includes('摘要')) || textareas[0];
                if (summaryInput && summaryInput.value !== desc && desc) {{
                    summaryInput.value = desc;
                    summaryInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    action.push("Filled summary");
                }}

                const rows = Array.from(document.querySelectorAll('.form-item, .byte-form-item'));
                
                // 1. Category (分类) - Default: 人工智能
                const catRow = rows.find(r => r.innerText.includes('分类'));
                if (catRow) {{
                    const items = Array.from(catRow.querySelectorAll('.item'));
                    const aiItem = items.find(i => i.innerText.trim() === '人工智能');
                    if (aiItem && !aiItem.classList.contains('active')) {{
                        clickReactElement(aiItem);
                        action.push("Selected category: 人工智能");
                    }} else if (!items.some(i => i.classList.contains('active')) && items.length > 0) {{
                        items[0].click();
                        action.push("Selected fallback category");
                    }}
                }}
                
                // 2. Type into Tag input (标签) to trigger API search
                const tagRow = rows.find(r => r.innerText.includes('标签'));
                if (tagRow) {{
                    const input = tagRow.querySelector('input');
                    if (input) {{
                        setReactInputValue(input, '人工智能');
                        input.dispatchEvent(new Event('focus', {{bubbles: true}}));
                        clickReactElement(input);
                        action.push("Typed into tag input");
                    }}
                }}
                
                return action.join(", ");
            }} catch (err) {{
                return "Error: " + err.message;
            }}
        }})();
        """
        res1 = self.chrome.execute_javascript(w_idx, t_idx, js_publish_dialog_part1, settle_seconds=1.0)
        logger.info(f"Publish Dialog Part 1: {res1}")
        
        # 7. Wait for Juejin Tag API to return options
        logger.info("Waiting 1.5s for Juejin to query tags...")
        time.sleep(1.5)

        # 8. Click the resolved Tag option
        logger.info("Clicking the resolved tag option...")
        js_publish_dialog_part2 = f"""
        (function() {{
            try {{
                let action = [];
                function clickReactElement(el) {{
                    if (!el) return false;
                    const key = Object.keys(el).find(k => k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$'));
                    if (key && el[key] && el[key].onClick) {{
                        el[key].onClick({{
                            preventDefault: () => {{}},
                            stopPropagation: () => {{}},
                            nativeEvent: new MouseEvent('click', {{bubbles: true, cancelable: true}}),
                            isDefaultPrevented: () => false,
                            isPropagationStopped: () => false,
                            target: el,
                            currentTarget: el
                        }});
                        return true;
                    }}
                    el.click();
                    return true;
                }}
                
                // 2b. Click the resolved Tag option
                // Dropdowns are attached to body via React Portals.
                // We MUST filter out elements inside .form-item to avoid clicking the Category button instead!
                const allOptions = Array.from(document.querySelectorAll('.byte-select-option, .item, li'));
                const options = allOptions.filter(el => !el.closest('.form-item') && !el.closest('.byte-form-item'));
                const tagOption = options.find(o => o.innerText.trim() === '人工智能');
                if (tagOption) {{
                    clickReactElement(tagOption);
                    action.push("Selected tag option: 人工智能");
                }}
                
                // Close dropdown to persist selection natively without closing the dialog
                const safeArea = document.querySelector('.form-item, .byte-form-item');
                if (safeArea) {{
                    safeArea.click();
                }}
                
                return action.join(", ");
            }} catch (err) {{
                return "Error: " + err.message;
            }}
        }})();
        """
        res2 = self.chrome.execute_javascript(w_idx, t_idx, js_publish_dialog_part2, settle_seconds=1.0)
        logger.info(f"Publish Dialog Part 2: {res2}")
        
        # 9. Wait for tag to process to avoid blur cancellation
        logger.info("Waiting 0.5s for Juejin to process tag selection...")
        time.sleep(0.5)

        # 10. Fill Publish Dialog Data (Collection, Topic)
        logger.info("Setting up Publish Dialog (Collection & Topic)...")
        js_publish_dialog_part3 = f"""
        (function() {{
            try {{
                let action = [];
                const rows = Array.from(document.querySelectorAll('.form-item, .byte-form-item'));
                
                function clickReactElement(el) {{
                    if (!el) return false;
                    const key = Object.keys(el).find(k => k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$'));
                    if (key && el[key] && el[key].onClick) {{
                        el[key].onClick({{
                            preventDefault: () => {{}},
                            stopPropagation: () => {{}},
                            nativeEvent: new MouseEvent('click', {{bubbles: true, cancelable: true}}),
                            isDefaultPrevented: () => false,
                            isPropagationStopped: () => false,
                            target: el,
                            currentTarget: el
                        }});
                        return true;
                    }}
                    el.click();
                    return true;
                }}
                
                function setReactInputValue(input, value) {{
                    let lastValue = input.value;
                    input.value = value;
                    let event = new Event('input', {{ bubbles: true }});
                    event.simulated = true;
                    let tracker = input._valueTracker;
                    if (tracker) {{
                        tracker.setValue(lastValue);
                    }}
                    input.dispatchEvent(event);
                }}
                
                function selectDropdownOption(row, searchTexts) {{
                    const input = row.querySelector('input');
                    if (!input) return;
                    for (const searchText of searchTexts) {{
                        setReactInputValue(input, searchText);
                        input.dispatchEvent(new Event('focus', {{bubbles: true}}));
                        clickReactElement(input);
                        
                        const options = Array.from(document.querySelectorAll('.byte-select-option'));
                        const option = options.find(o => o.innerText.trim() === searchText);
                        if (option) {{
                            clickReactElement(option);
                            action.push("Selected option: " + searchText);
                        }} else {{
                            const optionInc = options.find(o => o.innerText.includes(searchText));
                            if (optionInc) {{
                                clickReactElement(optionInc);
                                action.push("Selected option: " + searchText);
                            }}
                        }}
                    }}
                }}
                
                // 3. Collection (收录至专栏) - Default: AI, agent
                const colRow = rows.find(r => r.innerText.includes('收录至专栏'));
                if (colRow) {{
                    selectDropdownOption(colRow, ['AI', 'agent']);
                }}
                
                // 4. Topic (创作话题) - Default: AI 编程
                const topicRow = rows.find(r => r.innerText.includes('创作话题'));
                if (topicRow) {{
                    selectDropdownOption(topicRow, ['AI 编程']);
                }}
                
                // Close dropdown to persist selection natively and unblock UI
                const safeArea2 = document.querySelector('.form-item, .byte-form-item');
                if (safeArea2) {{
                    safeArea2.click();
                }}
                
                return action.join(", ");
            }} catch (err) {{
                return "Error: " + err.message;
            }}
        }})();
        """
        res3 = self.chrome.execute_javascript(w_idx, t_idx, js_publish_dialog_part3, settle_seconds=1.0)
        logger.info(f"Publish Dialog Part 3: {res3}")

        logger.info("Juejin article configuration complete. Submitting article...")
        
        # 11. Final Submit
        js_submit = """
        (function() {{
            const buttons = Array.from(document.querySelectorAll('button, .byte-btn'));
            const submitBtn = buttons.find(b => b.innerText.includes('确定并发布') || b.innerText === '发布文章' || b.innerText === '确认发布');
            if (submitBtn) {{
                submitBtn.click();
                return "Clicked submit button: " + submitBtn.innerText;
            }}
            return "Submit button not found";
        }})();
        """
        res_submit = self.chrome.execute_javascript(w_idx, t_idx, js_submit, settle_seconds=2.0)
        logger.info(f"Publish final result: {res_submit}")
