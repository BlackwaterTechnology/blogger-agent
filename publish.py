import argparse

def cmd_wechat_publish(args: argparse.Namespace) -> None:
    from pathlib import Path
    from loguru import logger
    from chrome import ChromeDomController
    import time
    import json
    import subprocess
    import markdown

    md_path = Path(args.payload) / "ARC-AGI-文章.md"
    if not md_path.exists():
        raise SystemExit(f"Markdown file not found: {md_path}")
        
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    
    title = ""
    author = ""
    collection = "AI"
    desc_lines = []
    content_lines = []
    
    state = 0
    for line in lines:
        if line.startswith("# 标题"):
            state = 1
        elif line.startswith("# 作者"):
            state = 2
        elif line.startswith("# 简介"):
            state = 4
        elif line.startswith("# 集合"):
            state = 5
        elif line.startswith("# 正文") or line.startswith("---"):
            if line.startswith("# 正文"):
                state = 3
            else:
                state = 0
        elif state == 1 and line.strip():
            title = line.strip()
            state = 0
        elif state == 2 and line.strip():
            author = line.strip()
            state = 0
        elif state == 5 and line.strip():
            collection = line.strip()
            state = 0
        elif state == 4:
            desc_lines.append(line)
        elif state == 3:
            content_lines.append(line)
            
    content = "\n".join(content_lines).strip()
    desc = "\n".join(desc_lines).strip()
    
    if desc:
        if len(desc) < 60 or len(desc) > 120:
            logger.warning(f"Summary (简介) length is {len(desc)} chars. It should be between 60 and 120 chars!")
    
    # Parse Markdown to HTML
    try:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'sane_lists'])
        # Crucial: Remove all newlines from the generated HTML.
        # ProseMirror interprets literal \n characters in injected HTML as extra paragraphs/line breaks!
        html_content = html_content.replace('\n', '')
    except Exception as e:
        logger.warning(f"Failed to parse markdown, falling back to raw text: {e}")
        html_content = f"<p>{content.replace(chr(10), '<br>')}</p>"
        
    logger.info(f"Parsed Title: {title}")
    logger.info(f"Parsed Author: {author}")
    logger.info(f"Parsed Collection: {collection}")
    logger.info(f"Parsed Description: {desc[:20]}... ({len(desc)} chars)")
    logger.info(f"Parsed Content Length: {len(content)}")
    logger.info(f"Generated HTML Length: {len(html_content)}")
    
    system_chrome = ChromeDomController()
    
    try:
        w_idx, t_idx = system_chrome.find_global_tab(["https://mp.weixin.qq.com"])
        url = system_chrome.get_tab_url(w_idx, t_idx)
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
                system_chrome.set_tab_url(w_idx, t_idx, new_url, settle_seconds=5.0)
            except Exception as e:
                logger.warning(f"Failed to navigate: {e}")
        else:
            logger.warning("Could not extract token from URL. Cannot auto-navigate to editor.")
            
        logger.info("Waiting 15 seconds for editor to fully load...")
        time.sleep(15)
        
        try:
            w_idx, t_idx = system_chrome.find_global_tab(["https://mp.weixin.qq.com"])
            url = system_chrome.get_tab_url(w_idx, t_idx)
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
                
                document.execCommand('insertHTML', false, html);
                return "Filled via execCommand";
            }}
            
            return "Filled basic inputs, but could not find rich text editor.";
        }} catch (err) {{
            return "Error in JS: " + err.message;
        }}
    }})();
    """
    
    logger.info("Injecting content into editor...")
    try:
        inject_res = system_chrome.execute_javascript(w_idx, t_idx, js_inject, settle_seconds=1.0)
        logger.info(f"Injection result: {inject_res}")
    except Exception as e:
        logger.warning(f"JS injection failed: {e}")
        
    logger.info("Putting content into clipboard for manual pasting if needed.")
    
    # As a fallback, we copy the rich text to clipboard so the user can just press Cmd+V.
    # On macOS, textutil can convert HTML to RTF and pbcopy will store it as rich text!
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
    
    def run_ui_state_machine(name, js_code, max_steps=10, delay=1.5):
        logger.info(f"Starting UI State Machine: {name}")
        for step in range(1, max_steps + 1):
            res_str = system_chrome.execute_javascript(w_idx, t_idx, js_code)
            try:
                import json
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
                
                // Success Check: When Originality is successfully enabled, a green "Original:" badge appears 
                // next to the Author field, and the Author field becomes readonly.
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
            
            // Check for reward error
            const authorError = originalDialog.querySelector('.js_author_error');
            if (authorError && authorError.style.display !== 'none' && (authorError.innerText.includes('Reward') || authorError.innerText.includes('赞赏'))) {
                state.has_reward_error = true;
            }
            
            // Bypass the "Reward Account" validation bug if it appears
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
            
            // 1. Check agreement
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
            
            // 2. Click Confirm
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
    if not run_ui_state_machine("Original Setup", js_original_setup, max_steps=30):
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
            
            // 1. Check agreement
            const agreeCheckbox = rewardDialog.querySelector('input[type="checkbox"]');
            if (agreeCheckbox && !agreeCheckbox.checked) {
                agreeCheckbox.click();
                action = 'Checked agreement';
                return JSON.stringify({state: state, action: action, is_done: false});
            }
            
            // 2. Select account
            const nicknames = Array.from(rewardDialog.querySelectorAll('div.nickname, .weui-desktop-account__nickname'));
            if (nicknames.length > 0) {
                // If there's an obvious active class or radio button we could check, but clicking it is generally safe
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
            
            // 3. Click Confirm
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
    run_ui_state_machine("Reward Setup", js_reward_setup, max_steps=8)

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
    run_ui_state_machine("Collection Setup", js_collection_setup, max_steps=8)

def main():
    parser = argparse.ArgumentParser(description="WeChat Publish Script")
    parser.add_argument("--payload", default="docs/bloger-agent", help="Directory containing the article markdown files")
    args = parser.parse_args()
    cmd_wechat_publish(args)

if __name__ == "__main__":
    main()
