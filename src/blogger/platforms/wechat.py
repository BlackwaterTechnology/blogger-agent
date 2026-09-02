import re
import time
import json
import subprocess
from loguru import logger
from ..core.jxa_chrome import JxaChromeController

class WechatPublisher:
    def __init__(self):
        # WeChat 用 JxaChromeController (AppleScript/JXA) 走默认 user-data-dir 的
        # 日常 Chrome —— CDP Chrome 跑 mp.weixin 会被反爬检测弹"插件存在安全
        # 隐患"告警（微信开发者社区里官方建议无痕模式即可绕，但无痕模式不持久
        # cookies，不实用）。详见 commit 历史和 docs。
        #
        # 前置：你日常 Chrome 必须勾选 View → Developer →
        # Allow JavaScript from Apple Events，否则 execute javascript 失败。
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
        if article_data.get("type") == "photo" or (article_data.get("photo_paths") and len(article_data.get("photo_paths", [])) > 0):
            return self.publish_photo(article_data)
        return self.publish_article(article_data)

    def publish_photo(self, article_data: dict) -> None:
        title = article_data["title"]
        author = article_data.get("author", "Agent")
        desc = article_data.get("desc", "")
        content = article_data.get("content", "")
        collection = article_data.get("collection", "")
        photo_paths = article_data.get("photo_paths", [])

        if not photo_paths:
            logger.error("No photo paths found in article_data for photo message publishing.")
            raise ValueError("No photo paths provided for photo message")

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(f"WeChat Official Account tab not found in Chrome: {e}")

        logger.info(f"Found WeChat tab: {url}")

        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        token = qs.get("token", [""])[0]

        if not token:
            raise SystemExit("Could not extract token from WeChat tab URL. Please make sure you are logged into mp.weixin.qq.com.")

        # 1. Always navigate to a clean fresh photo editor tab to avoid mutating previous draft
        fresh_url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=8&token={token}&lang=en_US&timestamp={int(time.time()*1000)}"
        logger.info(f"Navigating to fresh WeChat Photo Message Editor: {fresh_url}")
        try:
            self.chrome.set_tab_url(w_idx, t_idx, fresh_url, settle_seconds=6.0)
        except Exception as e:
            logger.warning(f"Navigation warning: {e}")

        logger.info("Waiting for photo editor to fully initialize...")
        time.sleep(4.0)

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
            logger.info(f"Now on tab: {url}")
        except Exception as e:
            logger.warning(f"Could not re-resolve WeChat tab: {e}")

        # 2. Upload Photos Sequentially
        logger.info(f"Uploading {len(photo_paths)} photo card(s)...")
        import base64

        for idx, p_path in enumerate(photo_paths):
            if not p_path.exists():
                logger.warning(f"Photo file does not exist: {p_path}")
                continue

            b64_data = base64.b64encode(p_path.read_bytes()).decode('utf-8')
            filename = p_path.name

            js_upload_single = f"""
            (function() {{
                try {{
                    const b64Data = {json.dumps(b64_data)};
                    const filename = {json.dumps(filename)};
                    
                    const binStr = atob(b64Data);
                    const len = binStr.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {{
                        bytes[i] = binStr.charCodeAt(i);
                    }}
                    const blob = new Blob([bytes.buffer], {{ type: 'image/png' }});
                    const file = new File([blob], filename, {{ type: 'image/png' }});
                    
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    
                    const inputs = Array.from(document.querySelectorAll('.image-selector input[type="file"], .js_upload_btn_container input[type="file"], input[type="file"][multiple]'));
                    if (inputs.length === 0) return JSON.stringify({{ error: 'No upload input found' }});
                    
                    const targetInput = inputs[inputs.length - 1];
                    targetInput.files = dt.files;
                    targetInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    return JSON.stringify({{ success: true, filename: filename }});
                }} catch (e) {{
                    return JSON.stringify({{ error: e.message }});
                }}
            }})();
            """
            res = self.chrome.execute_javascript(w_idx, t_idx, js_upload_single, settle_seconds=0.5)
            logger.info(f"Upload card [{idx+1}/{len(photo_paths)}] {filename}: {res}")
            time.sleep(2.0)

        # 3. Inject Full Title (WeChat Photo Message hard limit: 20 chars)
        photo_title = title.strip()
        # If separator follows punctuation (？, ！, ：, ，), clean up separator without duplicate punctuation
        photo_title = re.sub(r'([？!！:：,，])\s*(\uff5c|\||\u2014\u2014|\u2014|-)\s*', r'\1', photo_title)
        # Otherwise replace remaining spaced separators with clean Chinese colon '：'
        photo_title = re.sub(r'\s*(\uff5c|\||\u2014\u2014|\u2014|-)\s*', '：', photo_title)
        photo_title = re.sub(r'\s+', '', photo_title)  # Remove residual spaces
        if len(photo_title) > 20:
            logger.warning(f"Photo message title '{photo_title}' exceeds WeChat 20-character limit ({len(photo_title)} chars)! Truncating safely to 20 chars.")
            photo_title = photo_title[:20].rstrip('：，？！')

        logger.info(f"Injecting full title: {photo_title}")
        js_inject_title = f"""
        (function() {{
            try {{
                const titleVal = {json.dumps(photo_title)};
                const titlePm = document.querySelector('.title-editor__input .ProseMirror, #js_title_main .ProseMirror');
                if (titlePm) {{
                    titlePm.focus();
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(titlePm);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    document.execCommand('delete', false, null);
                    document.execCommand('insertText', false, titleVal);
                    titlePm.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                const textarea = document.querySelector('textarea#title');
                if (textarea) {{
                    textarea.value = titleVal;
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                return "TITLE_SET";
            }} catch(e) {{
                return "Error setting title: " + e.message;
            }}
        }})();
        """
        title_res = self.chrome.execute_javascript(w_idx, t_idx, js_inject_title, settle_seconds=0.5)
        logger.info(f"Title injection result: {title_res}")

        # 4. Inject Body Text into Description Editor (rendered clean text as paragraphs)
        logger.info("Injecting rendered clean text into description editor...")
        from ..core.markdown_parser import render_markdown_to_clean_text
        body_clean = article_data.get("clean_text") or render_markdown_to_clean_text(content)

        # Defensive check against WeChat Photo Message 1000-char hard ceiling
        if len(body_clean) > 980:
            logger.warning(f"Photo companion text length ({len(body_clean)}) approaches WeChat 1000-char limit! Trimming safely...")
            trimmed = body_clean[:950]
            last_break = max(trimmed.rfind('\n'), trimmed.rfind('。'), trimmed.rfind('！'), trimmed.rfind('!'))
            if last_break > 700:
                body_clean = trimmed[:last_break+1].strip()
            else:
                body_clean = trimmed.strip()

        # Build clean HTML for WeChat Photo Message ProseMirror editor
        # ProseMirror schema for .share-text__input defines description as a single
        # block containing inline nodes and hard breaks (<br>). Multiple <p> tags
        # are unwrapped by ProseMirror DOMParser, which drops inter-paragraph breaks.
        # Converting all newlines (\n) to <br> within a single <p> preserves both
        # single line breaks and double blank-line paragraph breaks (<br><br>).
        clean_html_text = body_clean.replace('\n', '<br>')
        html_body = f'<p>{clean_html_text}</p>'

        js_inject_desc = f"""
        (function() {{
            try {{
                const htmlBody = {json.dumps(html_body)};
                const textVal = {json.dumps(body_clean)};
                const descEl = document.querySelector('.share-text__input .ProseMirror, .js_pmEditorArea .ProseMirror, .content_edit .share-text__input .ProseMirror');
                if (!descEl) return JSON.stringify({{ error: 'NO_DESC_EDITOR' }});
                
                descEl.focus();
                
                // Clear any pre-existing content safely
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(descEl);
                selection.removeAllRanges();
                selection.addRange(range);
                document.execCommand('delete', false, null);

                // Inject full HTML with <br> preserved
                descEl.innerHTML = htmlBody;
                descEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                descEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                // Also update any fallback textarea if present
                const textarea = document.querySelector('textarea#js_description, textarea.share-text__input');
                if (textarea) {{
                    textarea.value = textVal;
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                return JSON.stringify({{ success: true, length: descEl.innerText.length, brCount: descEl.querySelectorAll('br').length }});
            }} catch(e) {{
                return JSON.stringify({{ error: e.message }});
            }}
        }})();
        """
        desc_res = self.chrome.execute_javascript(w_idx, t_idx, js_inject_desc, settle_seconds=0.5)
        logger.info(f"Description injection result: {desc_res}")

        # 5. Setup Collection (合集设置)
        if collection:
            logger.info(f"Setting up Photo Collection: {collection}")
            js_photo_collection_setup = f"""
            (function() {{
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

                const targetCollection = {json.dumps(collection)};
                let state = {{ is_done: false }};
                let action = '';

                const collRow = document.querySelector('#js_article_tags_area');
                if (collRow && collRow.innerText && collRow.innerText.includes(targetCollection)) {{
                    state.is_done = true;
                    action = 'Collection already set';
                    return JSON.stringify({{ state, action, is_done: true }});
                }}

                const dialog = Array.from(document.querySelectorAll('.weui-desktop-dialog')).find(d => d.clientHeight > 0 && d.innerText.includes('Collection'));
                if (!dialog) {{
                    const toggle = document.querySelector('.js_article_tags_label') || document.querySelector('#js_article_tags_area');
                    if (toggle) {{
                        clickReactElement(toggle);
                        action = 'Opened collections dialog';
                        return JSON.stringify({{ state, action, is_done: false }});
                    }}
                    state.is_done = true;
                    action = 'No collection toggle found';
                    return JSON.stringify({{ state, action, is_done: true }});
                }}

                // In dialog: click input to show options or filter
                const input = dialog.querySelector('input');
                if (input) {{
                    input.focus();
                    input.click();
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, targetCollection);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}

                // Find matching option
                const options = Array.from(document.querySelectorAll('.select-opt-li, li')).filter(li => li.innerText && li.innerText.trim() === targetCollection);
                if (options.length > 0) {{
                    clickReactElement(options[0]);
                    const confirmBtn = Array.from(dialog.querySelectorAll('button')).find(b => (b.innerText.includes('Confirm') || b.innerText.includes('确定')) && !b.classList.contains('weui-desktop-btn_disabled'));
                    if (confirmBtn) {{
                        setTimeout(() => clickReactElement(confirmBtn), 150);
                        action = `Selected ${{targetCollection}} and clicked confirm`;
                        return JSON.stringify({{ state, action, is_done: false }});
                    }}
                }}

                action = `Waiting for collection option (${{targetCollection}})...`;
                return JSON.stringify({{ state, action, is_done: false }});
            }})();
            """
            self.run_ui_state_machine("Photo Collection Setup", w_idx, t_idx, js_photo_collection_setup, max_steps=12, delay=1.0)

        # 6. Setup Creation Source (原创/来源声明)
        logger.info("Setting up Creation Source...")
        js_photo_source_setup = """
        (function() {
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

            const sourceRow = document.querySelector('#js_claim_source_area');
            if (sourceRow && sourceRow.innerText && (sourceRow.innerText.includes('个人观点') || sourceRow.innerText.includes('AI生成'))) {
                state.is_done = true;
                action = 'Creation source already set';
                return JSON.stringify({ state, action, is_done: true });
            }

            const dialog = Array.from(document.querySelectorAll('.weui-desktop-dialog')).find(d => d.clientHeight > 0 && d.innerText.includes('Creation Source'));
            if (!dialog) {
                const toggle = document.querySelector('.js_claim_source_desc') || document.querySelector('#js_claim_source_area label');
                if (toggle) {
                    clickReactElement(toggle);
                    action = 'Opened creation source dialog';
                    return JSON.stringify({ state, action, is_done: false });
                }
                state.is_done = true;
                action = 'No creation source toggle found';
                return JSON.stringify({ state, action, is_done: true });
            }

            // In dialog: click radio for "个人观点，仅供参考" (value 4)
            const radios = dialog.querySelectorAll('input[type="radio"]');
            for (let r of radios) {
                if (r.value === '4' || r.parentElement.innerText.includes('个人观点')) {
                    r.click();
                    r.checked = true;
                    r.dispatchEvent(new Event('change', { bubbles: true }));
                    break;
                }
            }

            const confirmBtn = Array.from(dialog.querySelectorAll('button')).find(b => (b.innerText.includes('Confirm') || b.innerText.includes('确定')) && !b.classList.contains('weui-desktop-btn_disabled'));
            if (confirmBtn) {
                setTimeout(() => clickReactElement(confirmBtn), 150);
                action = 'Selected 个人观点 and confirmed';
                return JSON.stringify({ state, action, is_done: false });
            }

            action = 'Waiting for source confirm button...';
            return JSON.stringify({ state, action, is_done: false });
        })();
        """
        self.run_ui_state_machine("Photo Creation Source Setup", w_idx, t_idx, js_photo_source_setup, max_steps=12, delay=1.0)

        # 7. Setup Reward (赞赏设置)
        logger.info("Setting up Reward (赞赏)...")
        js_photo_reward_setup = """
        (function() {
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

            const isVisible = el => !!el && el.getBoundingClientRect().height > 0 && window.getComputedStyle(el).display !== 'none';
            let state = { is_done: false };
            let action = '';

            const area = document.querySelector('#js_reward_setting_area');
            if (area && area.innerText && (area.innerText.includes('Account:') || area.innerText.includes('赞赏账户'))) {
                state.is_done = true;
                action = 'Reward already enabled and bound to account';
                return JSON.stringify({ state, action, is_done: true });
            }

            const rewardDialog = Array.from(document.querySelectorAll('.weui-desktop-dialog, .reward-setting-dialog')).find(d => isVisible(d) && (d.innerText.includes('Reward') || d.innerText.includes('赞赏')));
            if (!rewardDialog) {
                if (area && isVisible(area)) {
                    const openBtn = area.querySelector('.js_reward_open, .setting-group__switch, .setting-group__content');
                    if (openBtn) {
                        clickReactElement(openBtn);
                        action = 'Clicked photo reward row to open dialog';
                        return JSON.stringify({ state, action, is_done: false });
                    }
                }
                state.is_done = true;
                action = 'Photo reward setting area not found, skipping';
                return JSON.stringify({ state, action, is_done: true });
            }

            // In Dialog:
            // 1. Select "Reward the Author" radio if present
            const authorRadio = Array.from(rewardDialog.querySelectorAll('input[type="radio"], .weui-desktop-form__check-label, label, span')).find(r => r.innerText && (r.innerText.includes('Author') || r.innerText.includes('赞赏作者')));
            if (authorRadio) {
                clickReactElement(authorRadio);
            }

            // 2. Select Recent account if present
            const recentAccount = rewardDialog.querySelector('.recent-select div:last-child, .recent-select div, .search-result__item');
            if (recentAccount && isVisible(recentAccount)) {
                clickReactElement(recentAccount);
            }

            // 3. Check agreement checkbox
            const agreeCheckbox = rewardDialog.querySelector('.reward-setting-dialog__footer input[type="checkbox"], input[type="checkbox"]');
            if (agreeCheckbox && !agreeCheckbox.checked) {
                agreeCheckbox.click();
            }

            // 4. Click Confirm
            const btns = Array.from(rewardDialog.querySelectorAll('button'));
            const confirmBtn = btns.find(b => (b.innerText.includes('Confirm') || b.innerText.includes('确定')) && !b.classList.contains('weui-desktop-btn_disabled'));
            if (confirmBtn) {
                setTimeout(() => clickReactElement(confirmBtn), 150);
                action = 'Confirmed photo reward setup';
                return JSON.stringify({ state, action, is_done: false });
            }

            action = 'Waiting for reward confirm button...';
            return JSON.stringify({ state, action, is_done: false });
        })();
        """
        self.run_ui_state_machine("Photo Reward Setup", w_idx, t_idx, js_photo_reward_setup, max_steps=10, delay=1.0)

        # Summary of Photo Message Publishing
        print("\n" + "="*50)
        print("🎉 WeChat Photo Message (图片消息) Draft Ready!")
        print("="*50)
        print(f"✓ 标题: {photo_title}")
        print(f"✓ 图片卡片: {len(photo_paths)} 张已全部上传并设置为 3:4 画册")
        print(f"✓ 封面: 默认第一张卡片 ({photo_paths[0].name})")
        print("✓ 伴随文案: 已自动填充至描述输入框")
        print(f"✓ 合集属性: {collection or '未设置'}")
        print("✓ 来源声明: 个人观点，仅供参考")
        print("✓ 赞赏设置: 已自动开启并绑定账号")
        print("ℹ️ 建议在微信编辑器中核对后点击右下角「保存为草稿」")
        print("="*50 + "\n")

    def publish_article(self, article_data: dict) -> None:
        title = article_data["title"]
        author = article_data["author"]
        desc = article_data["desc"]
        content = article_data["content"]
        html_content = article_data["html_content"]
        collection = article_data["collection"]
        cover_path = article_data["cover_path"]
        local_images = article_data.get("wechat_local_images", article_data.get("local_images", []))
        image_captions = article_data.get("wechat_image_captions", article_data.get("image_captions", []))

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
                const html = {json.dumps(html_content)};
                
                const setEditorValue = (element, value) => {{
                    if (!element) return;
                    element.focus();
                    
                    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {{
                        element.select();
                        document.execCommand('insertText', false, value);
                        let proto = window.HTMLInputElement.prototype;
                        if (element.tagName === 'TEXTAREA') proto = window.HTMLTextAreaElement.prototype;
                        const setter = Object.getOwnPropertyDescriptor(proto, "value");
                        if (setter && setter.set) {{
                            setter.set.call(element, value);
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }} else {{
                        const selection = window.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(element);
                        selection.removeAllRanges();
                        selection.addRange(range);
                        
                        const dt = new DataTransfer();
                        dt.setData('text/plain', value);
                        const pasteEvent = new ClipboardEvent('paste', {{ bubbles: true, cancelable: true, clipboardData: dt }});
                        const handled = !element.dispatchEvent(pasteEvent);
                        
                        if (!handled) {{
                            document.execCommand('insertText', false, value);
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                }};
                
                // ONLY look at VISIBLE elements to avoid hidden proxy inputs that misdirect commands
                const allEditors = Array.from(document.querySelectorAll('.ProseMirror, input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea')).filter(e => e.clientHeight > 0);
                const pmEditors = allEditors.filter(e => e.classList && e.classList.contains('ProseMirror'));
                
                // Helper to get placeholder safely (works for divs and inputs)
                const getPh = (e) => (e.getAttribute('placeholder') || e.placeholder || e.getAttribute('data-placeholder') || '').toLowerCase();
                
                // 1. Identify Title Editor
                let tInput = allEditors.find(e => e.id === 'title' || getPh(e).includes('标题') || getPh(e).includes('title'));
                if (!tInput && pmEditors.length > 0) {{
                    tInput = pmEditors[0]; // fallback to first ProseMirror
                }}
                
                // 2. Identify Author Editor
                let aInput = allEditors.find(e => e !== tInput && (e.id === 'author' || getPh(e).includes('作者') || getPh(e).includes('author')));
                if (!aInput && pmEditors.length > 1) {{
                    aInput = pmEditors[1];
                }}
                
                // 3. Identify Main Content Editor
                let mainEditor = allEditors.find(e => e.id === 'js_editor');
                if (!mainEditor) {{
                    // The main content editor is usually the last ProseMirror that isn't title/author
                    const unassigned = pmEditors.filter(e => e !== tInput && e !== aInput);
                    if (unassigned.length > 0) {{
                        mainEditor = unassigned[unassigned.length - 1];
                    }}
                }}
                
                // Inject values
                if (tInput) setEditorValue(tInput, title);
                if (aInput) setEditorValue(aInput, author);
                
                if (desc) {{
                    let descInput = allEditors.find(e => e !== mainEditor && (e.id === 'js_description' || getPh(e).includes('摘要') || getPh(e).includes('summary')));
                    if (descInput) {{
                        setEditorValue(descInput, desc);
                    }}
                }}
                
                if (mainEditor) {{
                    mainEditor.focus();
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(mainEditor);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    return "READY_FOR_PASTE";
                }}
                
                return "Could not find main editor.";
            }} catch (err) {{
                return "Error in JS: " + err.message + "\\n" + err.stack;
            }}
        }})();
        """
        
        logger.info("Injecting content into editor...")
        try:
            inject_res = self.chrome.execute_javascript(w_idx, t_idx, js_inject, settle_seconds=1.0)
            logger.info(f"Injection result: {inject_res}")
            if inject_res and inject_res.strip() == "READY_FOR_PASTE":
                logger.info("Main editor focused and ready. Copying HTML to clipboard and pasting via Cmd+V...")
                import binascii
                html_hex = binascii.hexlify(html_content.encode('utf-8')).decode('utf-8')
                plain_hex = binascii.hexlify(content.encode('utf-8')).decode('utf-8')
                
                # Use AppleScript to set both HTML and UTF8 plain text to the OS clipboard
                applescript_set_clipboard = f'set the clipboard to {{«class utf8»:«data utf8{plain_hex}», «class HTML»:«data HTML{html_hex}»}}'
                try:
                    subprocess.run(["osascript", "-e", applescript_set_clipboard], check=True)
                    
                    self.chrome.run_in_chrome_process('''
                        keystroke "v" using {command down}
                    ''')
                    logger.info("Successfully pasted HTML content via OS clipboard.")
                    time.sleep(2.0)
                except Exception as e:
                    logger.warning(f"Failed to paste HTML via OS clipboard: {e}")
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
                            const placeholder = "__PLACEHOLDER__";
                            
                            // Re-identify main editor like in js_inject
                            const allEditors = Array.from(document.querySelectorAll('.ProseMirror, input:not([type="hidden"]), textarea')).filter(e => e.clientHeight > 0);
                            const pmEditors = allEditors.filter(e => e.classList && e.classList.contains('ProseMirror'));
                            const getPh = (e) => (e.getAttribute('placeholder') || e.placeholder || e.getAttribute('data-placeholder') || '').toLowerCase();
                            
                            let tInput = allEditors.find(e => e.id === 'title' || getPh(e).includes('标题') || getPh(e).includes('title'));
                            if (!tInput && pmEditors.length > 0) tInput = pmEditors[0];
                            let aInput = allEditors.find(e => e !== tInput && (e.id === 'author' || getPh(e).includes('作者') || getPh(e).includes('author')));
                            if (!aInput && pmEditors.length > 1) aInput = pmEditors[1];
                            let mainEditor = allEditors.find(e => e.id === 'js_editor');
                            if (!mainEditor) {{
                                const unassigned = pmEditors.filter(e => e !== tInput && e !== aInput);
                                if (unassigned.length > 0) mainEditor = unassigned[unassigned.length - 1];
                            }}
                            
                            // Find the deepest element containing the placeholder text
                            const elements = Array.from(document.body.querySelectorAll('*'));
                            let targetEl = elements.find(el => 
                                el.textContent && el.textContent.includes(placeholder) && 
                                Array.from(el.children).every(c => !c.textContent || !c.textContent.includes(placeholder))
                            );
                            
                            let editor = targetEl ? (targetEl.closest('.ProseMirror') || targetEl.closest('[contenteditable="true"]')) : mainEditor;
                            if (!editor) return "Editor not found";
                            
                            editor.focus();
                            const selection = window.getSelection();
                            const range = document.createRange();
                            
                            if (targetEl) {{
                                const meaningful = Array.from(targetEl.childNodes).filter(n => {{
                                    if (n.nodeType === 3) return n.nodeValue.trim().length > 0;
                                    if (n.nodeType === 1) return n.tagName !== 'BR';
                                    return false;
                                }});
                                
                                const collapseBlock = meaningful.length > 0 && targetEl.textContent.trim() === placeholder;
                                
                                if (collapseBlock) {{
                                    range.selectNode(targetEl);
                                }} else {{
                                    const textNode = Array.from(targetEl.childNodes).find(n => n.nodeType === 3 && n.nodeValue.includes(placeholder));
                                    if (textNode) {{
                                        const startOffset = textNode.nodeValue.indexOf(placeholder);
                                        range.setStart(textNode, startOffset);
                                        range.setEnd(textNode, startOffset + placeholder.length);
                                    }} else {{
                                        range.selectNode(targetEl);
                                    }}
                                }}
                                selection.removeAllRanges();
                                selection.addRange(range);
                                return "SELECTED";
                            }} else {{
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
                            }}
                        }} catch(e) {{
                            return e.message;
                        }}
                    }})();
                    """
                    js_find_and_select = js_find_and_select.replace('"__PLACEHOLDER__"', json.dumps(placeholder))
                    
                    res = self.chrome.execute_javascript(w_idx, t_idx, js_find_and_select, settle_seconds=0.5)
                    logger.info(f"Select placeholder result: {res}")
                    
                    # ProseMirror's paste handler reads the TIFF off the OS
                    # clipboard and uploads to WeChat's CDN. The osascript
                    # block targets process "Google Chrome" by name — if both
                    # the regular and the CDP Chrome are running concurrently,
                    # `tell application "Google Chrome"` resolves to whichever
                    # System Events selects first (usually the older / front
                    # one). Bring your regular Chrome to the front before
                    # running publisher to disambiguate.
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
                    const editors = document.querySelectorAll('.ProseMirror');
                    let editor = null;
                    for (let e of editors) {{
                        if (e.querySelector('img.wxw-img')) {{
                            editor = e; break;
                        }}
                    }}
                    if (!editor) return 'no editor with images';
                    
                    const captions = {json.dumps(image_captions)};
                    const isEmptyBlock = el => {{
                        if (!el) return false;
                        if (el.tagName !== 'P' && el.tagName !== 'SECTION' && el.tagName !== 'DIV') return false;
                        if (el.querySelector('img, pre, table, ul, ol, blockquote, hr, iframe, video')) return false;
                        const txt = (el.innerText || '').replace(/[\\u200B-\\u200D\\uFEFF\\n\\r\\t ]/g, '').trim();
                        return txt.length === 0;
                    }};
                    const captionStyle = 'text-align:center; font-size:13px; color:#888888; line-height:1.6; margin:4px 0 4px; padding:0 8px;';
                    let captioned = 0, removed = 0;
                    
                    const getImgs = () => Array.from(editor.querySelectorAll('img.wxw-img'));
                    const initialImgsCount = getImgs().length;
                    
                    for (let i = 0; i < initialImgsCount; i++) {{
                        let currentImgs = getImgs();
                        if (i >= currentImgs.length) break;
                        
                        let top = currentImgs[i];
                        while (top.parentElement && top.parentElement !== editor) top = top.parentElement;
                        
                        // Fix the native 24px margin gap that looks like an empty line
                        top.style.marginBottom = '2px';
                        
                        const caption = (captions[i] || '').trim();
                        
                        let emptyCount = 0;
                        let curr = top.nextElementSibling;
                        while (curr && isEmptyBlock(curr)) {{
                            emptyCount++;
                            curr = curr.nextElementSibling;
                        }}
                        
                        let isLast = false;
                        if (emptyCount > 0) {{
                            let lastEmpty = top;
                            for(let j=0; j<emptyCount; j++) lastEmpty = lastEmpty.nextElementSibling;
                            if (!lastEmpty || !lastEmpty.nextElementSibling) isLast = true;
                        }}
                        
                        if (emptyCount > 0) {{
                            let keepCount = caption ? 1 : 0;
                            if (isLast && emptyCount > keepCount) {{
                                keepCount++; 
                            }}
                            
                            let deleteCount = emptyCount - keepCount;
                            
                            // Delete extra empty blocks by simulating Backspace
                            for (let d = 0; d < deleteCount; d++) {{
                                currentImgs = getImgs();
                                if (i < currentImgs.length) {{
                                    top = currentImgs[i];
                                    while (top.parentElement && top.parentElement !== editor) top = top.parentElement;
                                }}
                                
                                let toDelete = top;
                                for (let j = 0; j <= keepCount; j++) {{
                                    if (toDelete) toDelete = toDelete.nextElementSibling;
                                }}
                                if (toDelete) {{
                                    editor.focus();
                                    const sel = window.getSelection();
                                    const range = document.createRange();
                                    range.setStart(toDelete, 0);
                                    range.collapse(true);
                                    sel.removeAllRanges();
                                    sel.addRange(range);
                                    if (document.execCommand('delete')) {{
                                        removed++;
                                    }}
                                }}
                            }}
                            
                            // Apply caption to the kept empty block
                            if (caption) {{
                                currentImgs = getImgs();
                                if (i < currentImgs.length) {{
                                    top = currentImgs[i];
                                    while (top.parentElement && top.parentElement !== editor) top = top.parentElement;
                                }}
                                let target = top.nextElementSibling;
                                if (target && isEmptyBlock(target)) {{
                                    editor.focus();
                                    const sel = window.getSelection();
                                    const range = document.createRange();
                                    range.selectNodeContents(target);
                                    sel.removeAllRanges();
                                    sel.addRange(range);
                                    document.execCommand('insertText', false, caption);
                                    target.setAttribute('style', captionStyle);
                                    captioned++;
                                }}
                            }}
                        }} else if (caption) {{
                            // ProseMirror didn't leave an empty block, but we need a caption!
                            // We create an empty block by simulating Enter at the end of the image section
                            editor.focus();
                            const sel = window.getSelection();
                            const range = document.createRange();
                            range.selectNode(top);
                            range.collapse(false); // End of image section
                            sel.removeAllRanges();
                            sel.addRange(range);
                            
                            document.execCommand('insertParagraph');
                            
                            // The newly inserted paragraph is now top.nextElementSibling
                            let newTarget = top.nextElementSibling;
                            if (newTarget) {{
                                range.selectNodeContents(newTarget);
                                sel.removeAllRanges();
                                sel.addRange(range);
                                document.execCommand('insertText', false, caption);
                                newTarget.setAttribute('style', captionStyle);
                                captioned++;
                            }}
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
                        const allEditors = Array.from(document.querySelectorAll('.ProseMirror')).filter(e => e.clientHeight > 0);
                        if (allEditors.length === 0) return "Editor not found";
                        let editor = allEditors[allEditors.length - 1];
                        
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
                
                self.chrome.run_in_chrome_process('''
                    keystroke "v" using {command down}
                ''')
                logger.info("Successfully initiated cover image paste/upload.")
                # Wait longer for cover image to upload and be indexed by WeChat
                time.sleep(6.0)
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
        # Inject the expected total number of images (inline + cover) to avoid race conditions 
        # picking the wrong image before the cover has finished uploading.
        expected_total_images = len(local_images) + (1 if cover_path else 0)
        js_cover_setup = f"""
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

                let state = {{ is_done: false }};
                let action = '';

                const coverPreview = document.querySelector('.js_cover_preview_square, .cover_preview_wrapper, .js_cover_preview_new, .first_appmsg_cover');
                if (coverPreview && coverPreview.clientHeight > 0) {{
                    state.is_done = true;
                    action = 'Cover already set';
                    return JSON.stringify({{state: state, action: action, is_done: true}});
                }}

                if (window.__wechat_automation_cover_done_clicked && (Date.now() - window.__wechat_automation_cover_done_clicked < 5000)) {{
                    action = 'Waiting for cover preview to render...';
                    return JSON.stringify({{state: state, action: action, is_done: false}});
                }}

                const dialogs = Array.from(document.querySelectorAll('.weui-desktop-dialog'));
                const activeDialog = dialogs.find(d => d.style.display !== 'none' && d.clientHeight > 0);
                
                if (activeDialog) {{
                    const btns = Array.from(activeDialog.querySelectorAll('button'));
                    
                    const isImageDialog = activeDialog.innerText.includes('Select an image') || activeDialog.innerText.includes('选择图片');
                    
                    if (isImageDialog) {{
                        const nextBtn = btns.find(b => b.innerText.includes('Next') || b.innerText.includes('下一步'));
                        if (nextBtn && nextBtn.clientHeight > 0) {{
                            const items = Array.from(activeDialog.querySelectorAll('.appmsg_content_img_item'));
                            const selected = items.find(i => i.classList.contains('selected') || i.querySelector('.selected'));
                            
                            if (!selected && items.length > 0) {{
                                const expected = {expected_total_images};
                                if (items.length < expected) {{
                                    action = `Waiting for cover to appear in dialog (current: ${{items.length}}, expected: ${{expected}})`;
                                    return JSON.stringify({{state: state, action: action, is_done: false}});
                                }}
                                clickReactElement(items[items.length - 1]);
                                action = 'Selected last image in dialog (cover)';
                                return JSON.stringify({{state: state, action: action, is_done: false}});
                            }}
                            
                            if (selected && !nextBtn.classList.contains('weui-desktop-btn_disabled')) {{
                                setTimeout(() => clickReactElement(nextBtn), 200);
                                action = 'Clicked Next in image dialog';
                                return JSON.stringify({{state: state, action: action, is_done: false}});
                            }}
                        }}
                    }} else {{
                        const doneBtn = btns.find(b => b.innerText.includes('Confirm') || b.innerText.includes('Done') || b.innerText.includes('完成') || b.innerText.includes('确定') || b.innerText.includes('Next') || b.innerText.includes('下一步'));
                        if (doneBtn && doneBtn.clientHeight > 0 && !doneBtn.classList.contains('weui-desktop-btn_disabled')) {{
                            window.__wechat_automation_cover_done_clicked = Date.now();
                            setTimeout(() => clickReactElement(doneBtn), 200);
                            action = 'Clicked Done in crop dialog';
                            return JSON.stringify({{state: state, action: action, is_done: false}});
                        }}
                    }}
                    
                    action = 'Waiting in dialog...';
                    return JSON.stringify({{state: state, action: action, is_done: false}});
                }}

                const selectBtns = Array.from(document.querySelectorAll('.js_selectCoverFromContent'));
                const visibleSelectBtn = selectBtns.find(b => b.clientHeight > 0 || b.offsetWidth > 0);
                if (visibleSelectBtn) {{
                    clickReactElement(visibleSelectBtn);
                    action = 'Clicked Choose from content';
                    return JSON.stringify({{state: state, action: action, is_done: false}});
                }}
                
                const emptyCover = document.querySelector('.select-cover__btn');
                const filledCoverWrap = document.querySelector('.js_chooseCoverWrap');
                
                if (emptyCover && (emptyCover.clientHeight > 0 || emptyCover.offsetWidth > 0)) {{
                    const mouseEnterEvent = new MouseEvent('mouseenter', {{ bubbles: true, cancelable: true }});
                    emptyCover.dispatchEvent(mouseEnterEvent);
                    clickReactElement(emptyCover);
                }}
                
                if (filledCoverWrap && (filledCoverWrap.clientHeight > 0 || filledCoverWrap.offsetWidth > 0)) {{
                    const mouseEnterEvent = new MouseEvent('mouseenter', {{ bubbles: true, cancelable: true }});
                    filledCoverWrap.dispatchEvent(mouseEnterEvent);
                    clickReactElement(filledCoverWrap);
                }}
                
                if (selectBtns.length > 0) {{
                    for (let btn of selectBtns) {{
                        clickReactElement(btn);
                    }}
                    action = 'Hovered cover area and clicked Choose from content';
                    return JSON.stringify({{state: state, action: action, is_done: false}});
                }}

                action = 'Cover UI not found';
                return JSON.stringify({{state: state, action: action, is_done: false}});
            }} catch (e) {{
                return JSON.stringify({{state: {{error: e.toString()}}, action: 'Error: ' + e.toString(), is_done: false}});
            }}
        }})();
        """

        if cover_path:
            self.run_ui_state_machine("Cover Setup", w_idx, t_idx, js_cover_setup, max_steps=15)
            
            logger.info("Deleting the cover image from the end of the article...")
            js_delete_cover = """
            (function() {
                try {
                    const allEditors = Array.from(document.querySelectorAll('.ProseMirror')).filter(e => e.clientHeight > 0);
                    if (allEditors.length === 0) return "Editor not found";
                    const editor = allEditors[allEditors.length - 1];

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
                        let alreadyTarget = false;
                        let foundContainer = null;
                        let searchDepth = 0;

                        // Walk up looking for the SMALLEST ancestor whose innerText
                        // contains a status indicator. That ancestor IS the row
                        // container (it wraps both the "创作声明" label and the
                        // current value). Walking past it pulls in sibling form
                        // rows and the click-target search latches onto the wrong
                        // row (e.g. 原创声明 row's "未声明" or some unrelated icon),
                        // so 8 iterations all click nothing useful.
                        //
                        // STATUS_OPENABLE = states from which we should re-open the
                        // dialog to switch to 个人观点. Note: 原创/转载 are NOT
                        // valid Creation Source values — they belong to a
                        // different field (原创声明) and including them here
                        // caused false matches against that sibling row.
                        const STATUS_OPENABLE = ['未声明', '未设置', '未添加', 'Not added', '内容由人工智能'];
                        const STATUS_TARGET = ['个人观点', 'Personal opinion'];

                        while(container && container.tagName.toLowerCase() !== 'body' && searchDepth < 5) {
                            const t = container.innerText || '';
                            const hasOpenable = STATUS_OPENABLE.some(k => t.includes(k));
                            const hasTarget = STATUS_TARGET.some(k => t.includes(k));

                            if (hasOpenable) {
                                // Current state is some non-target value (most
                                // commonly 未声明 on a fresh draft). Open the
                                // dialog. If hasTarget is also true it's text
                                // leaked from a tooltip / radio option — trust
                                // the openable indicator as the real state.
                                foundContainer = container;
                                alreadyTarget = false;
                                break;
                            }
                            if (hasTarget) {
                                foundContainer = container;
                                alreadyTarget = true;
                                break;
                            }
                            container = container.parentElement;
                            searchDepth++;
                        }

                        if (alreadyTarget) {
                            state.is_done = true;
                            action = 'Creation Source already set to 个人观点, skipping';
                            return JSON.stringify({state: state, action: action, is_done: true});
                        }

                        if (foundContainer) {
                            const clickables = Array.from(foundContainer.querySelectorAll('a, i, svg, span')).filter(el => el.clientHeight > 0);
                            const unstatedEl = clickables.find(el => {
                                const t = el.innerText || '';
                                return t.includes('未声明') || t.includes('未设置') || t.includes('未添加') || t.includes('Not added')
                                    || t.includes('内容由人工智能');
                            });

                            const iconEl = clickables.find(el => el.tagName.toLowerCase() === 'svg' || el.tagName.toLowerCase() === 'i' || el.classList.contains('weui-icon'));

                            const targets = [iconEl, unstatedEl, foundContainer].filter(Boolean);

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
                    action = 'Creation Source label not found, skipping';
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
