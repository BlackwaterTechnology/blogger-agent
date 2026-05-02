import time
import json
import subprocess
from loguru import logger
from ..core.jxa_chrome import JxaChromeController

class CsdnPublisher:
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
        collection = article_data.get("collection", "AI")

        # 1. Find CSDN Tab
        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://editor.csdn.net", "https://mp.csdn.net"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(f"CSDN tab not found in Chrome: {e}")
            
        logger.info(f"Found CSDN tab: {url}")
        
        # 2. Navigate to MD Editor
        if "editor.csdn.net/md" not in url:
            logger.info("Not currently on the markdown editor page. Navigating...")
            try:
                self.chrome.set_tab_url(w_idx, t_idx, "https://editor.csdn.net/md/", settle_seconds=2.0)
            except Exception as e:
                logger.warning(f"Failed to navigate: {e}")
                
            logger.info("Waiting for editor to fully load...")
            js_check_loaded = """
            (function() {
                const titleInput = document.querySelector('.article-bar__title, input[placeholder*="标题"]');
                const editor = document.querySelector('.editor, .CodeMirror');
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
            
        # 3. Inject Content
        js_inject_title = f"""
        (function() {{
            try {{
                const title = {json.dumps(title)};
                let action = [];
                
                // Set Title
                const titleInput = document.querySelector('.article-bar__title, input[placeholder*="标题"]');
                if (titleInput && titleInput.value !== title) {{
                    titleInput.value = title;
                    titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    action.push("Set Title");
                }}
                
                // Focus editor
                const editorElement = document.querySelector('.editor textarea, .CodeMirror textarea, textarea[class*="editor"]');
                if (editorElement) {{
                    editorElement.focus();
                    action.push("Focused editor textarea");
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

        # 1. Upload the illustration first if provided to get the CSDN CDN URL
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
                logger.info("Waiting for CSDN to upload the illustration...")
                js_extract_img = """
                (function() {
                    const el = document.querySelector('.editor, .CodeMirror');
                    if (!el) return "";
                    const text = el.innerText || el.textContent;
                    if (text.includes('上传中') || text.includes('Uploading')) return "UPLOADING";
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
                    lines = content.split('\\n')
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('#'):
                            insert_idx = i
                            break
                    
                    if insert_idx > 0:
                        content = "\\n".join(lines[:insert_idx]) + f"\\n\\n{illustration_markdown}\\n\\n" + "\\n".join(lines[insert_idx:])
                    else:
                        content = f"{illustration_markdown}\\n\\n{content}"
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

        # Paste the final combined content using Cmd+V
        logger.info("Pasting content into CSDN editor...")
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
                const btns = Array.from(document.querySelectorAll('button'));
                const publishBtn = btns.find(b => b.innerText && b.innerText.includes('发布文章') && !b.innerText.includes('定时'));
                if (publishBtn) {
                    publishBtn.click();
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
        
        # Add slight delay for dialog to appear
        time.sleep(2.0)
        
        # 5. Handle Cover Image
        if cover_path:
            logger.info(f"Found cover image: {cover_path}. Attempting to upload...")
            try:
                js_click_cover = """
                (function() {
                    try {
                        // Find the "从本地上传" element
                        const uploadAreas = Array.from(document.querySelectorAll('.el-upload, div, button, span')).filter(el => el.innerText && el.innerText.includes('从本地上传') && el.clientHeight > 0);
                        if (uploadAreas.length > 0) {
                            const target = uploadAreas[uploadAreas.length - 1];
                            
                            // Find the closest el-upload or focusable element, or make it focusable
                            let focusable = target.closest('.el-upload') || target.closest('button') || target;
                            focusable.setAttribute('tabindex', '0');
                            focusable.focus();
                            
                            return "READY_FOR_ENTER";
                        }
                        
                        return "Cover upload area not found";
                    } catch (err) {
                        return err.message;
                    }
                })();
                """
                
                res = self.chrome.execute_javascript(w_idx, t_idx, js_click_cover, settle_seconds=1.0)
                logger.info(f"Cover focus result: {res}")
                
                if "READY_FOR_ENTER" in res:
                    applescript_file_dialog = f'''
                    set the clipboard to "{cover_path.absolute()}"
                    tell application "System Events"
                        tell process "Google Chrome"
                            set frontmost to true
                            delay 0.5
                            -- Press Enter to trigger the focused upload button with a trusted event
                            key code 36
                            delay 2.0
                            
                            -- Now the system file dialog should be open
                            -- Press Cmd+Shift+G to go to folder
                            keystroke "G" using {{command down, shift down}}
                            delay 2.0
                            
                            -- Paste the file path
                            keystroke "v" using {{command down}}
                            delay 1.5
                            
                            -- Press Enter to confirm path
                            key code 36
                            delay 1.5
                            
                            -- Press Enter to select the file
                            key code 36
                        end tell
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", applescript_file_dialog], check=True)
                    logger.info("Successfully initiated cover image upload via trusted Enter and file dialog.")
                    time.sleep(4.0)
                    
                    # CSDN pops up an image cropper dialog after file selection, we need to click "确认上传"
                    js_confirm_cover = """
                    (function() {
                        try {
                            const btns = Array.from(document.querySelectorAll('button, div, span')).filter(b => b.innerText && b.innerText.includes('确认上传'));
                            const confirmBtn = btns.find(b => b.tagName === 'BUTTON' && b.clientHeight > 0) || btns[btns.length - 1];
                            
                            if (confirmBtn) {
                                if (confirmBtn.disabled || confirmBtn.classList.contains('is-disabled') || confirmBtn.classList.contains('disabled')) {
                                    return "Button is disabled, waiting...";
                                }
                                
                                // Native click
                                confirmBtn.click();
                                
                                // Dispatch MouseEvent
                                const evt = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                                confirmBtn.dispatchEvent(evt);
                                
                                // Click inner span if it exists (Element UI pattern)
                                const span = confirmBtn.querySelector ? confirmBtn.querySelector('span') : null;
                                if (span) {
                                    span.click();
                                    span.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                                }
                                
                                return "Clicked confirm upload";
                            }
                            return "Confirm upload button not found";
                        } catch(e) { return e.message; }
                    })();
                    """
                    confirm_success = False
                    for i in range(8):
                        res_confirm = self.chrome.execute_javascript(w_idx, t_idx, js_confirm_cover, settle_seconds=1.0)
                        logger.info(f"Confirm upload poll {i+1}: {res_confirm}")
                        if res_confirm and "Clicked" in str(res_confirm):
                            logger.info("Clicked cover image confirm upload button.")
                            confirm_success = True
                            time.sleep(2.0)
                            break
                        time.sleep(1.5)
                        
                    if not confirm_success:
                        logger.warning("Failed to click '确认上传' button, cover may not be saved.")
                else:
                    logger.warning(f"Skipping cover upload, area not found or focused: {res}")
            except Exception as e:
                logger.warning(f"Failed to upload cover image: {e}")

        # 6. Fill Publish Dialog Fields
        logger.info("Setting up Publish Dialog data (Summary, Type, Declaration, Category)...")
        js_publish_dialog_1 = f"""
        (function() {{
            try {{
                let action = [];
                const desc = {json.dumps(desc)};
                const collection = {json.dumps(collection)};
                
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

                // 1. Summary
                const textareas = Array.from(document.querySelectorAll('textarea'));
                const summaryInput = textareas.find(t => t.placeholder && t.placeholder.includes('摘要')) || textareas[0];
                if (summaryInput && summaryInput.value !== desc && desc) {{
                    summaryInput.value = desc;
                    summaryInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    action.push("Filled summary");
                }}

                // 2. Type (文章类型) - Original
                const typeLabels = Array.from(document.querySelectorAll('label, span, div')).filter(l => l.innerText && l.innerText.includes('原创'));
                if (typeLabels.length > 0) {{
                    const origLabel = typeLabels.find(l => l.querySelector('input[type="radio"]') || l.classList.contains('el-radio'));
                    if (origLabel) {{
                        clickReactElement(origLabel);
                        action.push("Selected Original Type");
                    }}
                }}

                // 3. Declaration (创作声明)
                // Find label "创作声明" and then its adjacent dropdown
                const labels = Array.from(document.querySelectorAll('label, div, span'));
                const decLabel = labels.find(l => l.innerText && l.innerText.trim() === '创作声明');
                if (decLabel) {{
                    const parent = decLabel.parentElement || decLabel.parentNode;
                    const decInput = parent.querySelector('input, .el-select, .el-input__inner');
                    if (decInput) {{
                        clickReactElement(decInput);
                        action.push("Clicked Declaration Dropdown");
                        setTimeout(() => {{
                            const options = Array.from(document.querySelectorAll('li, span, .el-select-dropdown__item')).filter(o => o.innerText && o.innerText.includes('部分内容由AI辅助生成'));
                            if (options.length > 0) clickReactElement(options[options.length-1]);
                        }}, 500);
                    }}
                }}

                // 4. Category (分类专栏)
                const categoryTags = Array.from(document.querySelectorAll('button, span, div, .tag-item, label')).filter(b => b.innerText && b.innerText.trim() === collection);
                if (categoryTags.length > 0) {{
                    const targetCategory = categoryTags.find(b => !b.classList.contains('el-select-dropdown__item'));
                    if (targetCategory) {{
                        clickReactElement(targetCategory);
                        action.push("Selected " + collection + " Category");
                    }}
                }}
                
                return JSON.stringify({{ action: action.join(", "), is_done: true }});
            }} catch (err) {{
                return JSON.stringify({{ error: err.message, is_done: false }});
            }}
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_publish_dialog_1, settle_seconds=1.5)

        # 6.5 Tags Configuration
        logger.info("Setting up Tags...")
        js_clear_tags = """
        (function() {
            let action = [];
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
            
            // Clear existing default tags
            const existingTags = Array.from(document.querySelectorAll('.tag__item, .el-tag'));
            for (let tag of existingTags) {
                const closeBtn = tag.querySelector('.el-icon-close, .icon-close, .close, .el-tag__close');
                if (closeBtn) {
                    clickReactElement(closeBtn);
                    action.push("Closed existing tag");
                }
            }

            // Click Add Tag
            const candidates = Array.from(document.querySelectorAll('button, div, span, .el-tag')).filter(b => 
                b.innerText && 
                (b.innerText.trim() === '添加文章标签' || b.innerText.trim() === '+ 添加文章标签' || b.innerText.trim() === '+添加文章标签')
            );
            
            // Prefer button, otherwise take the most deeply nested element (last in DOM)
            const tagBtn = candidates.find(b => b.tagName === 'BUTTON') || candidates[candidates.length - 1];
            
            if (tagBtn) {
                clickReactElement(tagBtn);
                tagBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                
                // Click inner span if it exists
                const span = tagBtn.querySelector ? tagBtn.querySelector('span') : null;
                if (span) {
                    span.click();
                    span.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                }
                action.push("Clicked add tag exact");
            } else {
                action.push("Add tag button NOT FOUND");
            }
            return JSON.stringify({ action: action.join(", ") });
        })();
        """
        res_tags = self.chrome.execute_javascript(w_idx, t_idx, js_clear_tags, settle_seconds=1.5)
        logger.info(f"Tag dialog open result: {res_tags}")
        
        # Wait for the tag input to appear and focus it
        logger.info("Polling for tag input field to focus...")
        js_focus_tag = """
        (function() {
            try {
                // Uniquely identify the tag input by its specific placeholder
                const inputs = Array.from(document.querySelectorAll('input'));
                const tagInput = inputs.find(i => i.placeholder && i.placeholder.includes('自定义标签'));
                
                if (tagInput && tagInput.clientHeight > 0) {
                    tagInput.focus();
                    return "FOCUSED";
                }
                return "Not found";
            } catch (err) { return err.message; }
        })();
        """
        is_focused = False
        for _ in range(5):
            res_focus = self.chrome.execute_javascript(w_idx, t_idx, js_focus_tag, settle_seconds=1.0)
            if res_focus == "FOCUSED":
                is_focused = True
                break
            time.sleep(1.0)
            
        if not is_focused:
            logger.warning("Tag input was not found or focused via JS. AppleScript will type into current active element.")
            
        # Now use AppleScript to type the tag and press Enter
        logger.info(f"Using AppleScript to input tag: {collection}")
        applescript_type_tag = f'''
        tell application "System Events"
            tell process "Google Chrome"
                set frontmost to true
                delay 0.5
                keystroke "{collection}"
                delay 1.5
                key code 36 -- Enter (confirm the autocomplete if any)
                delay 1.0
                key code 36 -- Enter (confirm the custom tag)
            end tell
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript_type_tag], check=True)
        time.sleep(1.5)

        # 6.6 Close Tag Dialog Explicitly via JS (avoids Esc key closing parent dialog)
        js_close_tag_dialog = """
        (function() {
            try {
                const dialogs = Array.from(document.querySelectorAll('.el-dialog'));
                // Find the one that specifically looks like the tag modal
                const tagDialog = dialogs.find(d => d.style.display !== 'none' && d.innerText.includes('标签') && d.innerText.includes('自定义标签'));
                if (tagDialog) {
                    const closeBtn = tagDialog.querySelector('.el-dialog__headerbtn, .el-icon-close, button[aria-label="Close"]');
                    if (closeBtn) {
                        closeBtn.click();
                        return "Closed tag dialog";
                    }
                }
                return "Tag dialog not found or already closed";
            } catch (err) { return err.message; }
        })();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_close_tag_dialog, settle_seconds=1.5)

        # 7. Final Submit
        logger.info("CSDN article configuration complete. Submitting article...")
        js_submit = """
        (function() {
            try {
                // Look for the submit button specifically inside the dialog to avoid clicking the main page trigger
                const dialogs = Array.from(document.querySelectorAll('.el-dialog, .dialog, .modal, .modal-box'));
                const activeDialog = dialogs.find(d => d.style.display !== 'none');
                const root = activeDialog || document;
                
                const btns = Array.from(root.querySelectorAll('button'));
                const submitBtn = btns.find(b => b.innerText && b.innerText.trim() === '发布文章' && !b.classList.contains('btn-cancel') && !b.classList.contains('btn-outline'));
                
                if (submitBtn) {
                    submitBtn.click(); 
                    return JSON.stringify({ action: "Found submit button", is_done: true });
                }
                return JSON.stringify({ action: "Submit button not found", is_done: false });
            } catch (err) {
                return JSON.stringify({ error: err.message, is_done: false });
            }
        })();
        """
        res_submit = self.chrome.execute_javascript(w_idx, t_idx, js_submit, settle_seconds=2.0)
        logger.info(f"Publish final result: {res_submit}")

