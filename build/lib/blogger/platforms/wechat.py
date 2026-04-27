import time
import json
import subprocess
from loguru import logger
from ..core.chrome import ChromeDomController

class WechatPublisher:
    def __init__(self):
        self.chrome = ChromeDomController()

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
        title = article_data["title"]
        author = article_data["author"]
        desc = article_data["desc"]
        content = article_data["content"]
        html_content = article_data["html_content"]
        collection = article_data["collection"]
        illustration_path = article_data["illustration_path"]
        cover_path = article_data["cover_path"]

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(f"WeChat Official Account tab not found in Chrome: {e}")
            
        logger.info(f"Found WeChat tab: {url}")
        
        if "appmsg_edit" not in url:
            logger.info("Not currently on the editor page. Extracting token to navigate directly to the editor...")
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            token = qs.get("token", [""])[0]
            
            if token:
                new_url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&token={token}&lang=en_US"
                logger.info(f"Navigating to New Article Editor: {new_url}")
                try:
                    self.chrome.set_tab_url(w_idx, t_idx, new_url, settle_seconds=5.0)
                except Exception as e:
                    logger.warning(f"Failed to navigate: {e}")
            else:
                logger.warning("Could not extract token from URL. Cannot auto-navigate to editor.")
                
            logger.info("Waiting 15 seconds for editor to fully load...")
            time.sleep(15)
            
            try:
                w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
                url = self.chrome.get_tab_url(w_idx, t_idx)
                logger.info(f"Now on tab: {url}")
            except Exception as e:
                logger.warning(f"Could not re-resolve WeChat tab: {e}")
                
        js_inject = f"""
        (function() {{
            try {{
                const title = {json.dumps(title)};
                const author = {json.dumps(author)};
                const desc = {json.dumps(desc)};
                const content = {json.dumps(content)};
                
                const setReactValue = (element, value) => {{
                    element.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, value);
                    element.blur();
                    
                    let proto = window.HTMLInputElement.prototype;
                    if (element.tagName.toUpperCase() === 'TEXTAREA') {{
                        proto = window.HTMLTextAreaElement.prototype;
                    }}
                    const setter = Object.getOwnPropertyDescriptor(proto, "value");
                    if (setter && setter.set) {{
                        setter.set.call(element, value);
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }};
                
                const inputs = Array.from(document.querySelectorAll('input, textarea'));
                const tInput = inputs.find(i => i.placeholder && (i.placeholder.includes('标题') || i.placeholder.includes('title'))) || document.getElementById('title');
                if (tInput) {{
                    setReactValue(tInput, title);
                }}
                const aInput = inputs.find(i => i.placeholder && (i.placeholder.includes('作者') || i.placeholder.includes('author'))) || document.getElementById('author');
                if (aInput) {{
                    setReactValue(aInput, author);
                }}
                
                if (desc) {{
                    const descInput = document.getElementById('js_description') || inputs.find(i => i.placeholder && (i.placeholder.includes('摘要') || i.placeholder.includes('summary') || i.placeholder.includes('Optional')));
                    if (descInput) {{
                        setReactValue(descInput, desc);
                    }}
                }}
                
                const html = {json.dumps(html_content)};
                
                if (typeof UE !== 'undefined' && UE.instants) {{
                    for (let key in UE.instants) {{
                        UE.instants[key].setContent(html);
                    }}
                    return "Filled via UE";
                }}
                
                let editor = document.querySelector('.ProseMirror');
                if (!editor) {{
                    const editors = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                    // Try to find the actual main editor by checking if it's large, or just grab the last one.
                    editor = editors.find(e => e.clientHeight > 100) || editors[editors.length - 1];
                }}
                
                if (editor) {{
                    editor.focus();
                    
                    // Explicitly set the DOM selection to select ALL content, so it overwrites existing text
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    // document.execCommand('insertHTML') strips format in newer WeChat editor versions.
                    // Simulate a paste event with clipboardData instead.
                    const dt = new DataTransfer();
                    dt.setData('text/html', html);
                    dt.setData('text/plain', content);
                    const pasteEvent = new ClipboardEvent('paste', {{
                        bubbles: true,
                        cancelable: true,
                        clipboardData: dt
                    }});
                    editor.dispatchEvent(pasteEvent);
                    
                    return "Filled via paste event";
                }}
                
                return "Filled basic inputs, but could not find rich text editor.";
            }} catch (err) {{
                return "Error in JS: " + err.message;
            }}
        }})();
        """
        
        logger.info("Injecting content into editor...")
        try:
            inject_res = self.chrome.execute_javascript(w_idx, t_idx, js_inject, settle_seconds=1.0)
            logger.info(f"Injection result: {inject_res}")
        except Exception as e:
            logger.warning(f"JS injection failed: {e}")
            
        if illustration_path:
            logger.info(f"Found illustration image: {illustration_path}. Inserting before first heading...")
            try:
                applescript_copy = f'set the clipboard to (read (POSIX file "{illustration_path.absolute()}") as TIFF picture)'
                self.chrome._run_osascript(applescript_copy)
                
                js_move_cursor = """
                (function() {
                    try {
                        let editor = document.querySelector('.ProseMirror');
                        if (!editor) return "Editor not found";
                        
                        editor.focus();
                        const selection = window.getSelection();
                        const range = document.createRange();
                        
                        const h1 = editor.querySelector('h1, h2, h3');
                        if (h1) {
                            range.setStartBefore(h1);
                            range.collapse(true);
                        } else {
                            range.selectNodeContents(editor);
                            range.collapse(true);
                        }
                        
                        selection.removeAllRanges();
                        selection.addRange(range);
                        return "Cursor moved";
                    } catch(e) {
                        return e.message;
                    }
                })();
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_move_cursor, settle_seconds=0.5)
                
                applescript_paste = '''
                tell application "System Events"
                    tell process "Google Chrome"
                        set frontmost to true
                        keystroke "v" using {command down}
                    end tell
                end tell
                '''
                self.chrome._run_osascript(applescript_paste)
                logger.info("Successfully initiated illustration image paste/upload.")
                time.sleep(2.0)
            except Exception as e:
                logger.warning(f"Failed to insert illustration image: {e}")

        if cover_path:
            logger.info(f"Found cover image: {cover_path}. Inserting at the end of the article...")
            try:
                applescript_copy = f'set the clipboard to (read (POSIX file "{cover_path.absolute()}") as TIFF picture)'
                self.chrome._run_osascript(applescript_copy)
                
                js_move_cursor_end = """
                (function() {
                    try {
                        let editor = document.querySelector('.ProseMirror');
                        if (!editor) return "Editor not found";
                        
                        editor.focus();
                        const selection = window.getSelection();
                        const range = document.createRange();
                        
                        range.selectNodeContents(editor);
                        range.collapse(false); // Move to end
                        
                        selection.removeAllRanges();
                        selection.addRange(range);
                        return "Cursor moved to end";
                    } catch(e) {
                        return e.message;
                    }
                })();
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_move_cursor_end, settle_seconds=0.5)
                
                applescript_paste = '''
                tell application "System Events"
                    tell process "Google Chrome"
                        set frontmost to true
                        keystroke "v" using {command down}
                    end tell
                end tell
                '''
                self.chrome._run_osascript(applescript_paste)
                logger.info("Successfully initiated cover image paste/upload.")
                time.sleep(2.0)
            except Exception as e:
                logger.warning(f"Failed to insert cover image: {e}")
            
        logger.info("Putting content into clipboard for manual pasting if needed.")
        
        try:
            p_textutil = subprocess.Popen(['textutil', '-stdin', '-format', 'html', '-inputencoding', 'utf-8', '-convert', 'rtf', '-stdout'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            rtf_output, _ = p_textutil.communicate(html_content.encode('utf-8'))
            
            p_pbcopy = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p_pbcopy.communicate(rtf_output)
        except Exception as e:
            logger.warning(f"Failed to copy RTF to clipboard, falling back to plain text: {e}")
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(content.encode('utf-8'))
            
        logger.info("Content copied to clipboard. If the text is missing, you can manually click inside the editor and press Cmd+V.")
        
        logger.info("Setting up cover...")
        js_cover_setup = """
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

                let state = { is_done: false };
                let action = '';

                const coverPreview = document.querySelector('.js_cover_preview_square, .cover_preview_wrapper, .js_cover_preview_new, .first_appmsg_cover');
                if (coverPreview && coverPreview.clientHeight > 0) {
                    state.is_done = true;
                    action = 'Cover already set';
                    return JSON.stringify({state: state, action: action, is_done: true});
                }

                if (window.__wechat_automation_cover_done_clicked && (Date.now() - window.__wechat_automation_cover_done_clicked < 5000)) {
                    action = 'Waiting for cover preview to render...';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }

                const dialogs = Array.from(document.querySelectorAll('.weui-desktop-dialog'));
                const activeDialog = dialogs.find(d => d.style.display !== 'none' && d.clientHeight > 0);
                
                if (activeDialog) {
                    const btns = Array.from(activeDialog.querySelectorAll('button'));
                    
                    const isImageDialog = activeDialog.innerText.includes('Select an image') || activeDialog.innerText.includes('选择图片');
                    
                    if (isImageDialog) {
                        const nextBtn = btns.find(b => b.innerText.includes('Next') || b.innerText.includes('下一步'));
                        if (nextBtn && nextBtn.clientHeight > 0) {
                            const items = Array.from(activeDialog.querySelectorAll('.appmsg_content_img_item'));
                            const selected = items.find(i => i.classList.contains('selected') || i.querySelector('.selected'));
                            
                            if (!selected && items.length > 0) {
                                clickReactElement(items[items.length - 1]);
                                action = 'Selected last image in dialog (cover)';
                                return JSON.stringify({state: state, action: action, is_done: false});
                            }
                            
                            if (selected && !nextBtn.classList.contains('weui-desktop-btn_disabled')) {
                                setTimeout(() => clickReactElement(nextBtn), 200);
                                action = 'Clicked Next in image dialog';
                                return JSON.stringify({state: state, action: action, is_done: false});
                            }
                        }
                    } else {
                        const doneBtn = btns.find(b => b.innerText.includes('Confirm') || b.innerText.includes('Done') || b.innerText.includes('完成') || b.innerText.includes('确定') || b.innerText.includes('Next') || b.innerText.includes('下一步'));
                        if (doneBtn && doneBtn.clientHeight > 0 && !doneBtn.classList.contains('weui-desktop-btn_disabled')) {
                            window.__wechat_automation_cover_done_clicked = Date.now();
                            setTimeout(() => clickReactElement(doneBtn), 200);
                            action = 'Clicked Done in crop dialog';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        }
                    }
                    
                    action = 'Waiting in dialog...';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }

                const selectBtns = Array.from(document.querySelectorAll('.js_selectCoverFromContent'));
                const visibleSelectBtn = selectBtns.find(b => b.clientHeight > 0 || b.offsetWidth > 0);
                if (visibleSelectBtn) {
                    clickReactElement(visibleSelectBtn);
                    action = 'Clicked Choose from content';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }
                
                const emptyCover = document.querySelector('.select-cover__btn');
                const filledCoverWrap = document.querySelector('.js_chooseCoverWrap');
                
                if (emptyCover && (emptyCover.clientHeight > 0 || emptyCover.offsetWidth > 0)) {
                    const mouseEnterEvent = new MouseEvent('mouseenter', { bubbles: true, cancelable: true });
                    emptyCover.dispatchEvent(mouseEnterEvent);
                    clickReactElement(emptyCover);
                }
                
                if (filledCoverWrap && (filledCoverWrap.clientHeight > 0 || filledCoverWrap.offsetWidth > 0)) {
                    const mouseEnterEvent = new MouseEvent('mouseenter', { bubbles: true, cancelable: true });
                    filledCoverWrap.dispatchEvent(mouseEnterEvent);
                    clickReactElement(filledCoverWrap);
                }
                
                if (selectBtns.length > 0) {
                    for (let btn of selectBtns) {
                        clickReactElement(btn);
                    }
                    action = 'Hovered cover area and clicked Choose from content';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }

                action = 'Cover UI not found';
                return JSON.stringify({state: state, action: action, is_done: false});
            } catch (e) {
                return JSON.stringify({state: {error: e.toString()}, action: 'Error: ' + e.toString(), is_done: false});
            }
        })();
        """
        if cover_path:
            self.run_ui_state_machine("Cover Setup", w_idx, t_idx, js_cover_setup, max_steps=15)
            
            logger.info("Deleting the cover image from the end of the article...")
            js_delete_cover = """
            (function() {
                try {
                    let editor = document.querySelector('.ProseMirror');
                    if (!editor) return "Editor not found";
                    
                    const imgs = Array.from(editor.querySelectorAll('img'));
                    if (imgs.length > 0) {
                        const lastImg = imgs[imgs.length - 1];
                        
                        editor.focus();
                        const selection = window.getSelection();
                        const range = document.createRange();
                        
                        range.selectNode(lastImg);
                        selection.removeAllRanges();
                        selection.addRange(range);
                        
                        return "READY_TO_CUT";
                    }
                    return "No images found to delete";
                } catch(e) {
                    return e.message;
                }
            })();
            """
            del_res = self.chrome.execute_javascript(w_idx, t_idx, js_delete_cover, settle_seconds=0.5)
            if del_res == "READY_TO_CUT":
                applescript_cut = '''
                tell application "System Events"
                    tell process "Google Chrome"
                        set frontmost to true
                        delay 0.5
                        keystroke "x" using {command down}
                    end tell
                end tell
                '''
                self.chrome._run_osascript(applescript_cut)
                time.sleep(0.5)
                logger.info("Delete cover image result: Cut the selected image")
            else:
                logger.info(f"Delete cover image result: {del_res}")

        logger.info("Setting up Originality (Original)...")
        js_original_setup = """
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

                let state = { is_dialog_open: false, agreement_checked: false, has_reward_error: false, is_done: false };
                let action = '';

                const dialogs = Array.from(document.querySelectorAll('.weui-desktop-dialog'));
                const originalDialog = dialogs.find(d => d.style.display !== 'none' && d.clientHeight > 0 && (d.innerText.includes('Original') || d.innerText.includes('原创')));
                
                if (!originalDialog) {
                    state.is_dialog_open = false;
                    
                    const oriTag = document.querySelector('.appmsg_origianl_tag');
                    const authorInput = document.getElementById('author');
                    const isOriTagVisible = oriTag && oriTag.offsetWidth > 0;
                    const isAuthorReadonly = authorInput && authorInput.readOnly;
                    
                    if (isOriTagVisible || isAuthorReadonly) {
                        state.is_done = true;
                        action = 'Originality badge found (setup successful)';
                        return JSON.stringify({state: state, action: action, is_done: true});
                    }
                    
                    const originalToggleInput = document.querySelector('.js_ori_setting_checkbox');
                    if (originalToggleInput) {
                        if (!originalToggleInput.checked) {
                            if (window.__wechat_automation_confirm_clicked && (Date.now() - window.__wechat_automation_confirm_clicked < 10000)) {
                                action = 'Waiting for Originality API to process...';
                                return JSON.stringify({state: state, action: action, is_done: false});
                            }
                            if (originalToggleInput.parentElement) {
                                originalToggleInput.parentElement.click();
                            } else {
                                originalToggleInput.click();
                            }
                            action = 'Clicked originality label to open dialog';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        } else {
                            state.is_done = true;
                            action = 'Toggle already checked, dialog not needed';
                            return JSON.stringify({state: state, action: action, is_done: true});
                        }
                    }
                    action = 'Toggle not found, waiting for DOM...';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }
                
                state.is_dialog_open = true;
                
                const authorError = originalDialog.querySelector('.js_author_error');
                if (authorError && authorError.style.display !== 'none' && (authorError.innerText.includes('Reward') || authorError.innerText.includes('赞赏'))) {
                    state.has_reward_error = true;
                }
                
                if (state.has_reward_error) {
                    const rewardSwitch = originalDialog.querySelector('.js_reward_switch');
                    if (rewardSwitch) {
                        const rewardLabel = rewardSwitch.closest('label');
                        if (rewardSwitch.checked) {
                            if (rewardLabel) rewardLabel.click();
                            else rewardSwitch.click();
                            action = 'Forced unchecked hidden reward switch to bypass validation bug';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        } else if (!rewardSwitch.checked) {
                            if (rewardLabel) rewardLabel.click();
                            else rewardSwitch.click();
                            action = 'Toggled hidden reward switch to trigger validation update';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        }
                    }
                }
                
                const agreeLabel = Array.from(originalDialog.querySelectorAll('label')).find(l => l.innerText.includes('agree') || l.innerText.includes('同意'));
                const agreeCheckbox = agreeLabel ? agreeLabel.querySelector('input[type="checkbox"]') : originalDialog.querySelector('.weui-desktop-form__checkbox');
                if (agreeCheckbox) {
                    state.agreement_checked = agreeCheckbox.checked;
                    if (!state.agreement_checked) {
                        if (agreeLabel) {
                            agreeLabel.click();
                        } else {
                            agreeCheckbox.click();
                        }
                        action = 'Checked agreement';
                        return JSON.stringify({state: state, action: action, is_done: false});
                    }
                }
                
                const btns = Array.from(originalDialog.querySelectorAll('button'));
                const confirmBtn = btns.find(b => b.innerText.includes('Confirm') || b.innerText.includes('确定'));
                if (confirmBtn && !confirmBtn.classList.contains('weui-desktop-btn_disabled')) {
                    setTimeout(() => {
                        confirmBtn.click();
                    }, 200);
                    window.__wechat_automation_confirm_clicked = Date.now();
                    action = 'Clicked Confirm';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }
                
                action = 'No action available';
                return JSON.stringify({state: state, action: action, is_done: false});
            } catch (e) {
                return JSON.stringify({state: {error: e.toString()}, action: 'Error: ' + e.toString(), is_done: false});
            }
        })();
        """
        if not self.run_ui_state_machine("Original Setup", w_idx, t_idx, js_original_setup, max_steps=30):
            raise RuntimeError("Original Setup failed to complete. Aborting publish process to maintain consistent state.")

        logger.info("Setting up reward account...")
        js_reward_setup = """
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

                let state = { is_dialog_open: false, is_done: false };
                let action = '';

                const dialogs = Array.from(document.querySelectorAll('.weui-desktop-dialog'));
                const rewardDialog = dialogs.find(d => d.style.display !== 'none' && d.clientHeight > 0 && (d.innerText.includes('Reward') || d.innerText.includes('赞赏') || d.innerText.includes('Confirm') || d.innerText.includes('确定')));
                
                if (!rewardDialog) {
                    state.is_dialog_open = false;
                    const rewardToggle = document.querySelector('.js_reward_setting_checkbox, .js_reward_setting');
                    if (rewardToggle) {
                        if (!rewardToggle.checked) {
                            rewardToggle.click();
                            action = 'Clicked reward toggle to open dialog';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        } else {
                            state.is_done = true;
                            action = 'Toggle already checked, dialog not needed';
                            return JSON.stringify({state: state, action: action, is_done: true});
                        }
                    }
                    state.is_done = true;
                    action = 'Toggle not found, skipping reward';
                    return JSON.stringify({state: state, action: action, is_done: true});
                }
                
                state.is_dialog_open = true;
                
                const agreeCheckbox = rewardDialog.querySelector('input[type="checkbox"]');
                if (agreeCheckbox && !agreeCheckbox.checked) {
                    agreeCheckbox.click();
                    action = 'Checked agreement';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }
                
                const nicknames = Array.from(rewardDialog.querySelectorAll('div.nickname, .weui-desktop-account__nickname'));
                if (nicknames.length > 0) {
                    const selected = rewardDialog.querySelector('.weui-desktop-account_selected, input[type="radio"]:checked');
                    if (!selected) {
                        nicknames[0].click();
                        action = 'Clicked account';
                        return JSON.stringify({state: state, action: action, is_done: false});
                    }
                } else {
                    const searchInput = rewardDialog.querySelector('input.weui-desktop-form__input');
                    if (searchInput) {
                        const activeDropdownItems = Array.from(document.querySelectorAll('.weui-desktop-dropdown__list li, .weui-desktop-picker__list li'));
                        const visibleItems = activeDropdownItems.filter(el => el.getBoundingClientRect().height > 0);
                        if (visibleItems.length > 0) {
                            visibleItems[0].click();
                            action = 'Selected account from dropdown';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        } else {
                            const mousedown = new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window});
                            searchInput.dispatchEvent(mousedown);
                            searchInput.click();
                            action = 'Clicked search input to open dropdown';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        }
                    }
                }
                
                const btns = Array.from(rewardDialog.querySelectorAll('button'));
                const confirmBtn = btns.find(b => b.innerText.includes('Confirm') || b.innerText.includes('确定'));
                if (confirmBtn && !confirmBtn.classList.contains('weui-desktop-btn_disabled')) {
                    setTimeout(() => clickReactElement(confirmBtn), 200);
                    action = 'Clicked Confirm';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }
                
                action = 'No action available';
                return JSON.stringify({state: state, action: action, is_done: false});
            } catch (e) {
                return JSON.stringify({state: {error: e.toString()}, action: 'Error: ' + e.toString(), is_done: false});
            }
        })();
        """
        self.run_ui_state_machine("Reward Setup", w_idx, t_idx, js_reward_setup, max_steps=8)

        logger.info(f"Setting up collection ({collection})...")
        import json as py_json
        js_collection_setup = f"""
        (function() {{
            try {{
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

                const collectionName = {py_json.dumps(collection)};
                let state = {{ is_dialog_open: false, is_done: false }};
                let action = '';

                const dialogs = Array.from(document.querySelectorAll('.weui-desktop-dialog'));
                const collectionDialog = dialogs.find(d => d.style.display !== 'none' && d.clientHeight > 0 && (d.innerText.includes('Collection') || d.innerText.includes('合集')));
                
                if (!collectionDialog) {{
                    state.is_dialog_open = false;
                    const collToggle = document.querySelector('.js_article_tags_label');
                    if (collToggle) {{
                        const collContent = document.querySelector('.js_article_tags_content');
                        if (collContent && collContent.innerText && collContent.innerText.trim() === collectionName) {{
                            state.is_done = true;
                            action = 'Collection setup successful';
                            return JSON.stringify({{state: state, action: action, is_done: true}});
                        }}
                        
                        if (window.__wechat_automation_confirm_clicked && (Date.now() - window.__wechat_automation_confirm_clicked < 3000)) {{
                            action = 'Waiting for dialog to close...';
                            return JSON.stringify({{state: state, action: action, is_done: false}});
                        }}
                        
                        clickReactElement(collToggle);
                        action = 'Clicked collection label to open dialog';
                        return JSON.stringify({{state: state, action: action, is_done: false}});
                    }}
                    state.is_done = true;
                    action = 'Toggle not found, skipping collection';
                    return JSON.stringify({{state: state, action: action, is_done: true}});
                }}
                
                state.is_dialog_open = true;
                
                const selectedItems = Array.from(collectionDialog.querySelectorAll('li.select, .weui-desktop-tag'));
                let hasSelectedTag = selectedItems.some(i => i.innerText && i.innerText.trim() === collectionName);
                
                const listItems = Array.from(collectionDialog.querySelectorAll('li'));
                const clickableItems = listItems.filter(i => i.innerText && i.innerText.trim() === collectionName && !i.classList.contains('select'));
                
                if (clickableItems.length > 0 && !hasSelectedTag) {{
                    clickReactElement(clickableItems[0]);
                    action = `Clicked collection (${{collectionName}})`;
                    return JSON.stringify({{state: state, action: action, is_done: false}});
                }} else if (!hasSelectedTag) {{
                    const searchInput = collectionDialog.querySelector('input[type="text"]');
                    if (searchInput && searchInput.value !== collectionName && !searchInput.disabled) {{
                        searchInput.focus();
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        setter.call(searchInput, collectionName);
                        searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        action = `Typed collection (${{collectionName}})`;
                        return JSON.stringify({{state: state, action: action, is_done: false}});
                    }} else if (searchInput && searchInput.value === collectionName) {{
                        action = `Waiting for collection dropdown for (${{collectionName}})...`;
                        return JSON.stringify({{state: state, action: action, is_done: false}});
                    }}
                }}
                
                if (hasSelectedTag) {{
                    const btns = Array.from(collectionDialog.querySelectorAll('button'));
                    const confirmBtn = btns.find(b => b.innerText.includes('Confirm') || b.innerText.includes('确定'));
                    if (confirmBtn && !confirmBtn.classList.contains('weui-desktop-btn_disabled')) {{
                        setTimeout(() => clickReactElement(confirmBtn), 200);
                        window.__wechat_automation_confirm_clicked = Date.now();
                        action = 'Clicked Confirm';
                        return JSON.stringify({{state: state, action: action, is_done: false}});
                    }}
                }}
                
                action = 'No action available';
                return JSON.stringify({{state: state, action: action, is_done: false}});
            }} catch (e) {{
                return JSON.stringify({{state: {{error: e.toString()}}, action: 'Error: ' + e.toString(), is_done: false}});
            }}
        }})();
        """
        if collection:
            self.run_ui_state_machine("Collection Setup", w_idx, t_idx, js_collection_setup, max_steps=8)
            
        logger.info("Saving as draft...")
        js_save_draft = """
        (function() {
            try {
                const buttons = Array.from(document.querySelectorAll('button, a.weui-desktop-btn, a[href="javascript:;"], div.weui-desktop-btn'));
                const saveDraft = buttons.find(b => b.innerText && (b.innerText.includes('Save as draft') || b.innerText.includes('保存草稿')));
                if (saveDraft) {
                    saveDraft.click();
                    return "Clicked Save as draft";
                }
                return "Save as draft button not found";
            } catch(e) {
                return e.message;
            }
        })();
        """
        save_res = self.chrome.execute_javascript(w_idx, t_idx, js_save_draft, settle_seconds=1.0)
        logger.info(f"Save as draft result: {save_res}")
