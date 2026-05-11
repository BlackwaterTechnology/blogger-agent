import time
import json
import subprocess
from loguru import logger
from ..core.cdp_chrome import CdpChromeController

class WechatPublisher:
    def __init__(self):
        self.chrome = CdpChromeController()

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
        cover_path = article_data["cover_path"]
        local_images = article_data.get("local_images", [])
        image_captions = article_data.get("image_captions", [])

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
        else:
            logger.info("Already on the editor page. Attempting to click 'Create New Content' for series article...")
            js_create_new = """
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

                    const allEls = Array.from(document.querySelectorAll('div, span, a, li, button'));
                    
                    // Step 1: Check if "Write new article" is visible
                    const writeNewArticleBtn = allEls.find(el => {
                        if (!el.innerText) return false;
                        const text = el.innerText.trim();
                        return (text === 'Write new article' || 
                                text === '写新图文' || 
                                text === '写新内容') && 
                                el.clientHeight > 0 && 
                                el.children.length <= 3 && 
                                (el.tagName === 'LI' || el.tagName === 'DIV' || el.tagName === 'A');
                    });

                    if (writeNewArticleBtn) {
                        clickReactElement(writeNewArticleBtn);
                        action = "Clicked 'Write new article' menu option";
                        return JSON.stringify({state: state, action: action, is_done: true});
                    }

                    // Step 2: Hover or Click "+ Create New Content"
                    const createBtn = allEls.find(el => {
                        if (!el.innerText) return false;
                        const text = el.innerText.trim();
                        return (text === '+ Create New Content' || 
                                text === 'Create New Content' || 
                                text === '+ 写新图文' || 
                                text === '写新图文' || 
                                text === '+ 新建消息' || 
                                text === '新建消息' ||
                                text === '+ 写新内容' ||
                                text === '写新内容') && 
                                el.clientHeight > 0 && 
                                el.children.length <= 3;
                    });
                    
                    if (createBtn) {
                        const mouseEnterEvent = new MouseEvent('mouseenter', { bubbles: true, cancelable: true });
                        createBtn.dispatchEvent(mouseEnterEvent);
                        clickReactElement(createBtn);
                        action = "Hovered/Clicked main '+ Create New Content' button, waiting for dropdown...";
                        return JSON.stringify({state: state, action: action, is_done: false});
                    }
                    
                    const fallbackBtn = allEls.find(el => {
                        if (!el.innerText) return false;
                        const text = el.innerText;
                        return (text.includes('Create New Content') || text.includes('写新图文') || text.includes('写新内容') || text.includes('新建消息')) && el.clientHeight > 0 && el.children.length === 0;
                    });
                    
                    if (fallbackBtn) {
                        let target = fallbackBtn;
                        if (fallbackBtn.parentElement && fallbackBtn.parentElement.clientHeight > 0) {
                            target = fallbackBtn.parentElement;
                        }
                        const mouseEnterEvent = new MouseEvent('mouseenter', { bubbles: true, cancelable: true });
                        target.dispatchEvent(mouseEnterEvent);
                        clickReactElement(target);
                        action = "Hovered/Clicked fallback button, waiting for dropdown...";
                        return JSON.stringify({state: state, action: action, is_done: false});
                    }
                    
                    action = "UI not found, retrying...";
                    return JSON.stringify({state: state, action: action, is_done: false});
                } catch(e) {
                    return JSON.stringify({state: {error: e.toString()}, action: 'Error: ' + e.toString(), is_done: false});
                }
            })();
            """
            try:
                self.run_ui_state_machine("Create Series Article", w_idx, t_idx, js_create_new, max_steps=8, delay=1.0)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Failed to execute create new content UI state machine: {e}")
                
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
            
        if local_images:
            logger.info(f"Found {len(local_images)} local images. Injecting them into the editor...")
            for img_path in local_images:
                logger.info(f"Uploading image: {img_path}")
                try:
                    # Set TIFF image to clipboard — global clipboard, no
                    # process targeting needed, can use plain osascript.
                    applescript_copy = f'set the clipboard to (read (POSIX file "{img_path.absolute()}") as TIFF picture)'
                    subprocess.run(["osascript", "-e", applescript_copy], check=True)
                    
                    placeholder = f"[UPLOAD_IMAGE: {img_path.absolute()}]"
                    
                    js_find_and_select = f"""
                    (function() {{
                        try {{
                            let editor = document.querySelector('.ProseMirror');
                            if (!editor) return "Editor not found";
                            
                            editor.focus();
                            const selection = window.getSelection();
                            const range = document.createRange();
                            
                            // Find the text node containing the placeholder
                            const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, null, false);
                            let node;
                            const placeholder = "__PLACEHOLDER__";
                            
                            while (node = walker.nextNode()) {{
                                if (node.nodeValue.includes(placeholder)) {{
                                    const startOffset = node.nodeValue.indexOf(placeholder);
                                    // 占位符在 markdown 里独占一行,parser 会把它包在自己的 <p> 里。
                                    // 如果只选占位符文字,粘贴图片后 ProseMirror 会留下一个空 <p>
                                    // 在图片下方,造成图文之间多一截空行(2026-05-10 实测)。
                                    // 当外层块级元素的可见文字只剩这个占位符时,直接选中整段
                                    // (含 <p>),让 paste 一把替换掉,空段就不会留下了。
                                    let blockEl = node.parentElement;
                                    while (blockEl && blockEl !== editor) {{
                                        const display = window.getComputedStyle(blockEl).display;
                                        if (display !== 'inline' && display !== 'inline-block') break;
                                        blockEl = blockEl.parentElement;
                                    }}
                                    // 只有当块内除了这条占位符文字以外没有别的可见子节点时,
                                    // 才扩选到整个块。否则同段里已粘进的图片或邻近文字会被一并替换掉。
                                    let collapseBlock = false;
                                    if (blockEl && blockEl !== editor) {{
                                        const meaningful = Array.from(blockEl.childNodes).filter(n => {{
                                            if (n.nodeType === 3) return n.nodeValue.trim().length > 0;
                                            if (n.nodeType === 1) return n.tagName !== 'BR';
                                            return false;
                                        }});
                                        collapseBlock = meaningful.length === 1 &&
                                            meaningful[0] === node &&
                                            node.nodeValue.trim() === placeholder;
                                    }}
                                    if (collapseBlock) {{
                                        range.selectNode(blockEl);
                                    }} else {{
                                        range.setStart(node, startOffset);
                                        range.setEnd(node, startOffset + placeholder.length);
                                    }}
                                    selection.removeAllRanges();
                                    selection.addRange(range);
                                    return "SELECTED";
                                }}
                            }}
                            
                            // Fallback: If no placeholder found (e.g. legacy front-matter illustration)
                            const h1 = editor.querySelector('h1, h2, h3');
                            if (h1) {{
                                range.setStartBefore(h1);
                                range.collapse(true);
                            }} else {{
                                range.selectNodeContents(editor);
                                range.collapse(true);
                            }}
                            selection.removeAllRanges();
                            selection.addRange(range);
                            return "FALLBACK_MOVED";
                        }} catch(e) {{
                            return e.message;
                        }}
                    }})();
                    """
                    js_find_and_select = js_find_and_select.replace('"__PLACEHOLDER__"', json.dumps(placeholder))
                    
                    res = self.chrome.execute_javascript(w_idx, t_idx, js_find_and_select, settle_seconds=0.5)
                    logger.info(f"Select placeholder result: {res}")
                    
                    # Cmd+V keystroke must hit the CDP Chrome (pid-anchored)
                    # rather than the user's day-to-day Chrome which may also
                    # be running. ProseMirror's paste handler reads the TIFF
                    # off the OS clipboard and uploads to WeChat's CDN.
                    self.chrome.run_in_chrome_process('''
                            keystroke "v" using {command down}
                    ''')
                    logger.info("Successfully initiated image paste/upload.")
                    time.sleep(2.5) # Wait for upload to complete
                except Exception as e:
                    logger.warning(f"Failed to insert image {{img_path}}: {e}")

            # 图片块后处理:ProseMirror 在每个 image <section> 后面会强制补一个
            # 空 <p>(里面是 ProseMirror-trailingBreak),即使下一个已经是可写 <p>
            # 也照补不误(2026-05-10 实测)。这个空段就成了图文之间多出的一截空白。
            # 策略:如果该图有 caption(markdown alt),就把这个空段填成图注样式
            # (居中、灰、小字号);否则把"夹在中间"的空段删掉(末尾空段保留,
            # ProseMirror 需要可写位置)。
            js_finalize_images = f"""
            (function(){{
                try {{
                    const editor = document.querySelector('.ProseMirror');
                    if (!editor) return 'no editor';
                    const captions = {json.dumps(image_captions)};
                    const isEmptyP = el => {{
                        if (!el || el.tagName !== 'P') return false;
                        if (el.querySelector('img, pre, table, ul, ol, blockquote, hr')) return false;
                        const txt = (el.innerText || '').replace(/[\\u200B-\\u200D\\uFEFF]/g, '').trim();
                        return txt.length === 0;
                    }};
                    const captionStyle = 'text-align:center; font-size:13px; color:#888888; line-height:1.6; margin:6px 0 14px; padding:0 8px;';
                    let captioned = 0, removed = 0;
                    const imgs = Array.from(editor.querySelectorAll('img.wxw-img'));
                    for (let i = 0; i < imgs.length; i++) {{
                        let top = imgs[i];
                        while (top.parentElement && top.parentElement !== editor) top = top.parentElement;
                        const caption = (captions[i] || '').trim();
                        let next = top.nextElementSibling;
                        if (caption && isEmptyP(next)) {{
                            // 把 trailing 空段就地改造成图注:走 selection + insertText
                            // 让文字进 ProseMirror 状态,然后直接改 style 属性。
                            editor.focus();
                            const sel = window.getSelection();
                            const range = document.createRange();
                            range.selectNodeContents(next);
                            sel.removeAllRanges();
                            sel.addRange(range);
                            document.execCommand('insertText', false, caption);
                            next.setAttribute('style', captionStyle);
                            captioned++;
                            continue;
                        }}
                        // 没 caption:把"夹在中间"的空段删掉
                        while (next && isEmptyP(next)) {{
                            const after = next.nextElementSibling;
                            if (!after) break;
                            editor.focus();
                            const sel = window.getSelection();
                            const range = document.createRange();
                            range.selectNode(next);
                            sel.removeAllRanges();
                            sel.addRange(range);
                            if (!document.execCommand('delete')) break;
                            removed++;
                            next = top.nextElementSibling;
                        }}
                    }}
                    return JSON.stringify({{captioned, removed}});
                }} catch(e) {{ return 'err: ' + e.message; }}
            }})();
            """
            try:
                fin_res = self.chrome.execute_javascript(w_idx, t_idx, js_finalize_images, settle_seconds=0.3)
                logger.info(f"Finalize images (caption/strip): {fin_res}")
            except Exception as e:
                logger.warning(f"Failed to finalize images: {e}")

        if cover_path:
            logger.info(f"Found cover image: {cover_path}. Inserting at the end of the article...")
            try:
                applescript_copy = f'set the clipboard to (read (POSIX file "{cover_path.absolute()}") as TIFF picture)'
                subprocess.run(["osascript", "-e", applescript_copy], check=True)
                
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
                
                # Cmd+V paste — pid-anchored to CDP Chrome.
                self.chrome.run_in_chrome_process('''
                            keystroke "v" using {command down}
                ''')
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
                    const editor = document.querySelector('.ProseMirror');
                    if (!editor) return "Editor not found";

                    // Filter out ProseMirror-separator (zero-size internal placeholder).
                    // Real WeChat content images carry the wxw-img class.
                    const realImgs = Array.from(editor.querySelectorAll('img.wxw-img'));
                    if (realImgs.length === 0) return "No real images found to delete";

                    const lastImg = realImgs[realImgs.length - 1];

                    // Walk up to the top-level child of the editor — typically a <section>
                    // wrapping just this image. Deleting the wrapper avoids leaving an empty section.
                    let topSection = lastImg;
                    while (topSection.parentElement && topSection.parentElement !== editor) {
                        topSection = topSection.parentElement;
                    }
                    if (topSection.parentElement !== editor) {
                        return "Cover image is not inside an editor child";
                    }

                    // If the wrapper holds more than just this image (e.g. surrounding text),
                    // narrow the deletion target to the image itself to avoid clobbering content.
                    const sectionText = (topSection.innerText || '').trim();
                    const otherImgs = topSection.querySelectorAll('img.wxw-img').length;
                    const target = (sectionText.length === 0 && otherImgs === 1) ? topSection : lastImg;

                    editor.focus();
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNode(target);
                    selection.removeAllRanges();
                    selection.addRange(range);

                    // execCommand('delete') routes through the contenteditable beforeinput
                    // pipeline, which ProseMirror handles via its own transaction — no
                    // AppleScript keystroke needed (which would lose focus).
                    const ok = document.execCommand('delete');
                    return ok ? "DELETED" : "execCommand('delete') returned false";
                } catch(e) {
                    return "Error: " + e.message;
                }
            })();
            """
            del_res = self.chrome.execute_javascript(w_idx, t_idx, js_delete_cover, settle_seconds=0.5)
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
                
                const searchInput = rewardDialog.querySelector('input.weui-desktop-form__input');
                const accountEmpty = !!searchInput && !searchInput.value.trim();
                const isVisible = el => !!el && el.getBoundingClientRect().height > 0;

                if (searchInput) {
                    // Search-input variant: the search input is the source of truth.
                    if (accountEmpty) {
                        // Preferred path: a "Recent" suggestion block is rendered next to the
                        // search input as `<div class="recent-select"><label>Recent</label><div>NAME</div></div>`.
                        // Without clicking it the Confirm button stays disabled and the dialog never closes.
                        const recentSelect = rewardDialog.querySelector('.recent-select');
                        if (isVisible(recentSelect)) {
                            const recentItem = Array.from(recentSelect.querySelectorAll('div'))
                                .find(d => (d.innerText || '').trim().length > 0);
                            if (recentItem) {
                                recentItem.click();
                                action = 'Clicked Recent account suggestion';
                                return JSON.stringify({state: state, action: action, is_done: false});
                            }
                        }
                        const dropdownItems = Array.from(document.querySelectorAll('.weui-desktop-dropdown__list li, .weui-desktop-picker__list li, .search-result__item'))
                            .filter(isVisible);
                        if (dropdownItems.length > 0) {
                            dropdownItems[0].click();
                            action = 'Selected account from dropdown';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        }
                        const mousedown = new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window});
                        searchInput.dispatchEvent(mousedown);
                        searchInput.click();
                        action = 'Clicked search input to open dropdown';
                        return JSON.stringify({state: state, action: action, is_done: false});
                    }
                    // Otherwise the input already holds an account name — fall through to Confirm.
                } else {
                    // List variant: the dialog renders nicknames inline. Restrict to visible
                    // elements (`.search-result__wrp` is hidden until typing).
                    const nicknames = Array.from(rewardDialog.querySelectorAll('div.nickname, .weui-desktop-account__nickname'))
                        .filter(isVisible);
                    if (nicknames.length > 0) {
                        // Restrict the "already selected" probe to the account-list area, not
                        // unrelated radios (e.g. the Reward Type radio group).
                        const accountArea = rewardDialog.querySelector('.reward-account-setting') || rewardDialog;
                        const selected = accountArea.querySelector('.weui-desktop-account_selected, .selected');
                        if (!selected) {
                            nicknames[0].click();
                            action = 'Clicked account';
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
            
        logger.info("Setting up Creation Source (Personal Opinion)...")
        js_creation_source_setup = """
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
                const sourceDialog = dialogs.find(d => d.style.display !== 'none' && d.clientHeight > 0 && (d.innerText.includes('Creation Source') || d.innerText.includes('创作声明')));
                
                if (!sourceDialog) {
                    state.is_dialog_open = false;
                    
                    if (window.__wechat_automation_source_confirm && (Date.now() - window.__wechat_automation_source_confirm < 5000)) {
                        state.is_done = true;
                        action = 'Creation Source setup successful (dialog closed)';
                        return JSON.stringify({state: state, action: action, is_done: true});
                    }
                    
                    const allLabels = Array.from(document.querySelectorAll('label, span, div'));
                    const sourceLabel = allLabels.find(el => {
                        const t = el.innerText ? el.innerText.trim() : '';
                        return t === '创作声明' || t === 'Creation Source';
                    });
                    
                    if (sourceLabel) {
                        let container = sourceLabel.parentElement;
                        let isUnset = false;
                        let searchDepth = 0;
                        
                        while(container && container.tagName.toLowerCase() !== 'body' && searchDepth < 5) {
                            const t = container.innerText || '';
                            if (t.includes('未声明') || t.includes('Not added') || t.includes('未设置') || t.includes('未添加')) {
                                isUnset = true;
                                break;
                            }
                            container = container.parentElement;
                            searchDepth++;
                        }
                        
                        if (isUnset && container && container.tagName.toLowerCase() !== 'body') {
                            const clickables = Array.from(container.querySelectorAll('a, i, svg, span')).filter(el => el.clientHeight > 0);
                            const unstatedEl = clickables.find(el => {
                                const t = el.innerText || '';
                                return t.includes('未声明') || t.includes('未设置') || t.includes('未添加') || t.includes('Not added');
                            });
                            
                            const iconEl = clickables.find(el => el.tagName.toLowerCase() === 'svg' || el.tagName.toLowerCase() === 'i' || el.classList.contains('weui-icon'));
                            
                            const targets = [iconEl, unstatedEl, container].filter(Boolean);
                            
                            for (let target of targets) {
                                clickReactElement(target);
                                try {
                                    target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                                    target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                                    target.click();
                                } catch (e) {}
                                
                                if (target.parentElement) {
                                    clickReactElement(target.parentElement);
                                    target.parentElement.click();
                                }
                            }
                            
                            action = 'Clicked Creation Source row to open dialog';
                            return JSON.stringify({state: state, action: action, is_done: false});
                        }
                    }
                    
                    state.is_done = true;
                    action = 'Creation Source seems already set or not found, skipping';
                    return JSON.stringify({state: state, action: action, is_done: true});
                }
                
                state.is_dialog_open = true;
                
                const labels = Array.from(sourceDialog.querySelectorAll('label'));
                const targetLabel = labels.find(l => {
                    const t = l.innerText || '';
                    return t.includes('个人观点，仅供参考') || t.includes('个人观点') || t.includes('Personal opinion');
                });
                
                if (targetLabel) {
                    const radio = targetLabel.querySelector('input[type="radio"]');
                    const isChecked = radio ? radio.checked : targetLabel.classList.contains('weui-desktop-form__radio_checked') || (targetLabel.querySelector('.weui-desktop-form__radio_checked') !== null);
                    
                    if (!isChecked) {
                        if (radio) {
                            radio.click();
                        } else {
                            clickReactElement(targetLabel);
                        }
                        action = 'Selected Personal Opinion radio button';
                        return JSON.stringify({state: state, action: action, is_done: false});
                    }
                }
                
                const btns = Array.from(sourceDialog.querySelectorAll('button'));
                const confirmBtn = btns.find(b => b.innerText.includes('Confirm') || b.innerText.includes('确定'));
                if (confirmBtn && !confirmBtn.classList.contains('weui-desktop-btn_disabled')) {
                    setTimeout(() => clickReactElement(confirmBtn), 200);
                    window.__wechat_automation_source_confirm = Date.now();
                    action = 'Clicked Confirm in Creation Source dialog';
                    return JSON.stringify({state: state, action: action, is_done: false});
                }
                
                action = 'Waiting in Creation Source dialog...';
                return JSON.stringify({state: state, action: action, is_done: false});
            } catch (e) {
                return JSON.stringify({state: {error: e.toString()}, action: 'Error: ' + e.toString(), is_done: false});
            }
        })();
        """
        self.run_ui_state_machine("Creation Source Setup", w_idx, t_idx, js_creation_source_setup, max_steps=8)

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
