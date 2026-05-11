import time
import json
import subprocess
from loguru import logger
from ..core.cdp_chrome import CdpChromeController, CdpChromeUnavailable

class CsdnPublisher:
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

    def publish(self, article_data: dict, *, dry_run: bool = False) -> None:
        """Publish the article. Set dry_run=True to fill the publish dialog but
        skip the final submit click — useful for previewing or for testing the
        flow without spamming the platform."""
        title = article_data.get("title", "")
        content = article_data.get("content", "")
        desc = article_data.get("desc", "")
        cover_path = article_data.get("cover_path")
        collection = article_data.get("collection", "AI")
        local_images = article_data.get("local_images", [])

        # 1. Find CSDN Tab — prefer the editor tab; fall back to any logged-in
        # csdn.net tab (blog/www/i/...) and navigate it to the editor.
        # Login session is shared across csdn.net subdomains via cookies.
        editor_prefixes = ["https://editor.csdn.net", "https://mp.csdn.net"]
        fallback_prefixes = [
            "https://blog.csdn.net",
            "https://www.csdn.net",
            "https://i.csdn.net",
            "https://bizhi.csdn.net",
            "https://download.csdn.net",
            "https://bbs.csdn.net",
            "https://csdn.net",
            "http://blog.csdn.net",
            "http://www.csdn.net",
            "http://csdn.net",
        ]
        try:
            w_idx, t_idx = self.chrome.find_global_tab(editor_prefixes)
        except Exception:
            try:
                w_idx, t_idx = self.chrome.find_global_tab(fallback_prefixes)
                logger.info("No editor tab open; reusing an existing CSDN tab — will navigate to the editor.")
            except Exception as e:
                raise SystemExit(
                    "CSDN tab not found in Chrome. Open any csdn.net page (blog/www/editor/...) "
                    f"in a logged-in tab and retry. Detail: {e}"
                )

        try:
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e:
            raise SystemExit(f"CSDN tab found but failed to read its URL: {e}")

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
                const editor = document.querySelector('.editor, .CodeMirror, textarea[class*="editor"]');
                if (titleInput && editor) {
                    return "LOADED";
                }
                return "LOADING";
            })();
            """
            for _ in range(20):
                try:
                    res = self.chrome.execute_javascript(w_idx, t_idx, js_check_loaded, settle_seconds=0.1)
                    if res == "LOADED":
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            
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
            self.chrome.run_in_chrome_process('''
                    keystroke "a" using {command down}
                    delay 0.1
                    key code 51 -- Delete key
                    delay 0.5
            ''')
        except Exception as e:
            logger.warning(f"Failed to clear editor: {e}")

        # 1. Upload the illustration first if provided to get the CSDN CDN URL
        if local_images:
            logger.info(f"Found {len(local_images)} local images. Extracting CDN links...")
            for img_path in local_images:
                try:
                    # Copy illustration to clipboard
                    applescript_copy_illus = f'set the clipboard to (read (POSIX file "{img_path.absolute()}") as TIFF picture)'
                    subprocess.run(["osascript", "-e", applescript_copy_illus], check=True)

                    # Paste into the empty editor — targeting CDP Chrome by pid.
                    self.chrome.run_in_chrome_process('''
                            keystroke "v" using {command down}
                    ''')
                    
                    # Poll for the uploaded URL via JS
                    logger.info(f"Waiting for CSDN to upload image {img_path.name}...")
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
                            first_heading_idx = None
                            for i, line in enumerate(lines):
                                if line.strip().startswith('#'):
                                    first_heading_idx = i
                                    break
                            
                            if first_heading_idx is not None:
                                content = "\n".join(lines[:first_heading_idx]) + f"\n\n{illustration_markdown}\n\n" + "\n".join(lines[first_heading_idx:])
                            else:
                                content = f"{illustration_markdown}\n\n{content}"
                        
                        # CLEAR EDITOR for next image — targeting CDP Chrome by pid.
                        self.chrome.run_in_chrome_process('''
                                keystroke "a" using {command down}
                                delay 0.1
                                key code 51 -- Delete key
                                delay 0.5
                        ''')
                    else:
                        logger.warning(f"Failed to extract uploaded image link for {img_path.name}.")
                        
                except Exception as e:
                    logger.warning(f"Failed to process image {img_path.name}: {e}")
                
        # 2. Clear editor for final content
        logger.info("Clearing editor for final content...")
        try:
            js_focus_for_clear = """
            (function() {
                const editorElement = document.querySelector('.editor textarea, .CodeMirror textarea, textarea[class*="editor"]');
                if (editorElement) {
                    editorElement.focus();
                    return "FOCUSED";
                }
                return "NOT_FOUND";
            })();
            """
            self.chrome.execute_javascript(w_idx, t_idx, js_focus_for_clear, settle_seconds=0.5)

            self.chrome.run_in_chrome_process('''
                    keystroke "a" using {command down}
                    delay 0.1
                    key code 51 -- Delete key
                    delay 0.5
            ''')
        except Exception as e:
            logger.warning(f"Failed to clear editor: {e}")

        # 3. Paste the final combined content using Cmd+V
        logger.info("Pasting final content into CSDN editor...")
        try:
            p_pbcopy = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p_pbcopy.communicate(content.encode('utf-8'))

            self.chrome.run_in_chrome_process('''
                    keystroke "v" using {command down}
            ''')
            time.sleep(2.0)
        except Exception as e:
            logger.warning(f"Failed to paste final content: {e}")

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
        
        # 5. Handle Cover Image via CDP DOM.setFileInputFiles.
        # CSDN's <input type="file"> sits inside an Element-UI .el-upload
        # wrapper. setFileInputFiles fires the same change event a real
        # user click would, which puts CSDN straight into its cropper
        # dialog — we still need to click "确认上传" afterwards.
        if cover_path:
            logger.info(f"Found cover image: {cover_path}. Uploading via CDP...")
            try:
                self.chrome.set_file_input(
                    t_idx,
                    '.el-upload input[type="file"]',
                    cover_path,
                )
                logger.info("Cover file injected via CDP DOM.setFileInputFiles; waiting for cropper...")
                time.sleep(4.0)

                # Cropper-confirm: poll for "确认上传" and click it.
                js_confirm_cover = """
                (function() {
                    try {
                        const btns = Array.from(document.querySelectorAll('button, div, span')).filter(b => b.innerText && b.innerText.includes('确认上传'));
                        const confirmBtn = btns.find(b => b.tagName === 'BUTTON' && b.clientHeight > 0) || btns[btns.length - 1];
                        if (confirmBtn) {
                            if (confirmBtn.disabled || confirmBtn.classList.contains('is-disabled') || confirmBtn.classList.contains('disabled')) {
                                return "Button is disabled, waiting...";
                            }
                            confirmBtn.click();
                            const evt = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                            confirmBtn.dispatchEvent(evt);
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
                confirm_clicked = False
                for i in range(8):
                    res_confirm = self.chrome.execute_javascript(w_idx, t_idx, js_confirm_cover, settle_seconds=1.0)
                    logger.info(f"Confirm upload poll {i+1}: {res_confirm}")
                    if res_confirm and "Clicked" in str(res_confirm):
                        logger.info("Clicked CSDN cover crop confirm.")
                        time.sleep(2.0)
                        confirm_clicked = True
                        break
                    time.sleep(1.5)
                if not confirm_clicked:
                    logger.warning("Failed to click '确认上传' button after CDP file injection.")
            except Exception as exc:
                logger.warning(f"Cover upload failed: {exc}")

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
                // We will handle category configuration in the next dedicated step because it requires opening a popup.
                
                return JSON.stringify({{ action: action.join(", "), is_done: true }});
            }} catch (err) {{
                return JSON.stringify({{ error: err.message, is_done: false }});
            }}
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_publish_dialog_1, settle_seconds=1.5)

        # Parse collection into a list (used by both tags and categories)
        if isinstance(collection, str):
            collection_list = [c.strip() for c in collection.replace('，', ',').replace(' ', ',').split(',') if c.strip()]
        elif isinstance(collection, list):
            collection_list = [str(c).strip() for c in collection if str(c).strip()]
        else:
            collection_list = [str(collection).strip()]

        # ============================================================
        # 6.2 Tags Configuration (文章标签) — MUST run BEFORE categories
        # ============================================================
        # CSDN Tag UI structure:
        #   .mark_selection_box (inline panel, NOT a dialog)
        #     .mark_add_tag_left (UL) — category sidebar
        #     .mark_add_tag_right — right panel with checkboxes
        #     input.el-input__inner with placeholder "请输入文字搜索，Enter键入可添加自定义标签"
        #   .mark_selection_box_selectTag — shows selected count
        logger.info("Setting up Tags via CSDN tag search input...")

        # JS to click "添加文章标签" button to open the tag panel
        js_click_add_tag = """
        (function() {
            // Specifically find the button with "添加文章标签" text
            const btns = Array.from(document.querySelectorAll('button.tag__btn-tag'));
            const tagBtn = btns.find(b => b.innerText && b.innerText.includes('添加文章标签'));
            if (tagBtn) { tagBtn.click(); return "CLICKED"; }
            // Fallback: broader search
            const candidates = Array.from(document.querySelectorAll('button, div, span')).filter(b =>
                b.innerText && b.innerText.replace(/\\s+/g, '').includes('添加文章标签')
            );
            const btn = candidates.find(b => b.tagName === 'BUTTON') || candidates[candidates.length - 1];
            if (btn) { btn.click(); return "CLICKED_FALLBACK"; }
            return "NOT_FOUND";
        })();
        """

        # JS to check if the tag panel (.mark_selection_box) is visible
        js_check_panel = """
        (function() {
            const panel = document.querySelector('.mark_selection_box');
            if (panel && panel.clientHeight > 0) {
                return "VISIBLE:" + panel.clientHeight;
            }
            return "NOT_VISIBLE";
        })();
        """

        # JS to find and focus the tag search input — ONLY focus, do NOT touch .value
        js_focus_tag_input = """
        (function() {
            const inputs = Array.from(document.querySelectorAll('input.el-input__inner, input[type="text"]'));
            const tagInput = inputs.find(i => i.placeholder && i.placeholder.includes('搜索'));
            if (tagInput && tagInput.clientHeight > 0) {
                tagInput.focus();
                tagInput.click();
                return "FOCUSED";
            }
            return "NOT_FOUND";
        })();
        """

        # Step 1: Open the tag panel
        res_click = self.chrome.execute_javascript(w_idx, t_idx, js_click_add_tag, settle_seconds=0.5)
        logger.info(f"Click add-tag button: {res_click}")

        # Step 2: Wait for the tag panel to appear
        panel_visible = False
        for attempt in range(10):
            res_panel = self.chrome.execute_javascript(w_idx, t_idx, js_check_panel, settle_seconds=0.3)
            if res_panel and str(res_panel).startswith("VISIBLE"):
                panel_visible = True
                logger.info(f"Tag panel appeared: {res_panel}")
                break
            time.sleep(0.5)

        if not panel_visible:
            logger.warning("Tag panel (.mark_selection_box) did not appear, skipping tags.")
        else:
            # Step 3: Clear any existing selected tags first
            js_clear_existing = """
            (function() {
                let cleared = 0;
                // Only remove the X buttons on already-selected tag pills
                const closeBtns = Array.from(document.querySelectorAll(
                    '.mark_selection .el-tag .el-icon-close, .mark_selection .el-tag__close'
                ));
                for (const btn of closeBtns) { btn.click(); cleared++; }
                return "Cleared " + cleared + " existing tags";
            })();
            """
            res_clear = self.chrome.execute_javascript(w_idx, t_idx, js_clear_existing, settle_seconds=0.5)
            logger.info(f"Clear existing tags: {res_clear}")
            time.sleep(0.5)

            # Step 4: For each tag, paste via clipboard and press Enter
            # CSDN placeholder: "请输入文字搜索，Enter键入可添加自定义标签"
            #
            # WHY PASTE instead of keystroke:
            # AppleScript `keystroke "Agent"` types character by character.
            # el-autocomplete searches after EACH character and auto-highlights
            # a suggestion (e.g. typing "A" → highlights "AI").
            # When Enter is pressed, it selects the highlighted suggestion
            # instead of adding the custom tag.
            # PASTE (Cmd+V) is instant — all characters appear at once.
            # With a 50ms delay before Enter, autocomplete hasn't appeared yet,
            # so Enter correctly triggers the "添加自定义标签" behavior.
            for tag_name in collection_list[:3]:
                logger.info(f"Adding tag: {tag_name!r}")

                # Focus the search input via JS (only focus, no value manipulation)
                res_focus = self.chrome.execute_javascript(w_idx, t_idx, js_focus_tag_input, settle_seconds=0.5)
                logger.info(f"  [tag={tag_name}] Focus input: {res_focus}")

                if "NOT_FOUND" in str(res_focus):
                    logger.warning(f"  [tag={tag_name}] Search input not found, skipping.")
                    continue

                # Copy tag name to system clipboard
                subprocess.run(["pbcopy"], input=tag_name.encode(), check=True)

                # Paste + Enter — targeting CDP Chrome by pid.
                try:
                    self.chrome.run_in_chrome_process('''
                        keystroke "a" using {command down}
                        delay 0.1
                        keystroke "v" using {command down}
                        delay 0.05
                        key code 36
                        delay 1.0
                    ''')
                    logger.info(f"  [tag={tag_name}] Pasted + Enter via clipboard")
                except Exception as e:
                    logger.warning(f"  [tag={tag_name}] AppleScript failed: {e}")

        # Close tag panel by clicking the X button before moving to categories
        js_close_tag_panel = """
        (function() {
            const panel = document.querySelector('.mark_selection_box');
            if (panel && panel.clientHeight > 0) {
                // Click the X close button inside the tag panel
                const closeBtn = panel.querySelector('button.modal__close-button');
                if (closeBtn) {
                    closeBtn.click();
                    return "Clicked close button";
                }
            }
            return "Tag panel already closed or no close button";
        })();
        """
        res_close = self.chrome.execute_javascript(w_idx, t_idx, js_close_tag_panel, settle_seconds=1.0)
        logger.info(f"Close tag panel: {res_close}")
        time.sleep(0.5)

        # ============================================================
        # 6.3 Category Configuration (分类专栏) — runs AFTER tags
        # ============================================================
        # CSDN Category UI structure:
        #   .form-entry containing "分类专栏" label
        #     .tag__box (h=32px, acts as anchor)
        #       .tag__item-list — currently selected categories
        #       button.tag__btn-tag "新建分类专栏" — opens NEW category input (NOT expand!)
        #       .tag__options-content (position:absolute, top:32px, z-index:2) — floating panel
        #         .tag__option-box — each existing category
        #           input.tag__option-chk (checkbox) — must click THIS directly, not parent
        #
        # IMPORTANT: Do NOT click "新建分类专栏" — it opens a tiny input for creating
        # a new category, not for expanding the existing list. The checkbox list
        # (.tag__options-content) is always present in DOM as a floating panel.
        # Must click input.tag__option-chk directly (not .tag__option-box) for Vue to react.
        logger.info("Setting up Category via checkbox selection...")

        # Step 1: Clear existing selected categories by clicking their checked checkboxes
        js_clear_cats = """
        (function() {
            const dialog = document.querySelector('.modal__publish-article, .modal__inner-1');
            if (!dialog) return "NO_DIALOG";
            const catEntry = Array.from(dialog.querySelectorAll('.form-entry')).find(d =>
                d.innerText && d.innerText.includes('分类专栏')
            );
            if (!catEntry) return "NO_CAT_SECTION";
            const tagBox = catEntry.querySelector('.tag__box');
            if (!tagBox) return "NO_TAG_BOX";
            let cleared = 0;
            const checkedBoxes = Array.from(tagBox.querySelectorAll('input.tag__option-chk:checked'));
            for (const cb of checkedBoxes) {
                cb.click();
                cleared++;
            }
            return "Cleared " + cleared + " categories";
        })();
        """
        res_clear = self.chrome.execute_javascript(w_idx, t_idx, js_clear_cats, settle_seconds=0.5)
        logger.info(f"Clear categories: {res_clear}")
        time.sleep(0.5)

        # Step 2: Select desired categories by clicking their checkboxes directly
        for cat_name in collection_list[:3]:
            logger.info(f"Selecting category: {cat_name!r}")
            js_select_cat = f"""
            (function() {{
                const dialog = document.querySelector('.modal__publish-article, .modal__inner-1');
                if (!dialog) return "NO_DIALOG";
                const catEntry = Array.from(dialog.querySelectorAll('.form-entry')).find(d =>
                    d.innerText && d.innerText.includes('分类专栏')
                );
                if (!catEntry) return "NO_CAT_SECTION";
                const tagBox = catEntry.querySelector('.tag__box');
                if (!tagBox) return "NO_TAG_BOX";
                const catName = {json.dumps(cat_name)};
                const optionBoxes = Array.from(tagBox.querySelectorAll('.tag__option-box'));
                for (const box of optionBoxes) {{
                    const text = (box.innerText || '').trim();
                    if (text === catName) {{
                        const cb = box.querySelector('input.tag__option-chk');
                        if (cb && cb.checked) {{
                            return "Already selected: " + catName;
                        }}
                        if (cb) {{
                            cb.click();
                            return "Selected: " + catName + " checked=" + cb.checked;
                        }}
                        return "No checkbox found for: " + catName;
                    }}
                }}
                return "Not found in list: " + catName;
            }})();
            """
            res_cat = self.chrome.execute_javascript(w_idx, t_idx, js_select_cat, settle_seconds=0.5)
            logger.info(f"  Category result: {res_cat}")
            time.sleep(0.3)

        # 7. Final Submit
        logger.info("CSDN article configuration complete.")
        if dry_run:
            logger.info("Dry-run mode: skipping final submit click. The publish dialog is left open for manual review.")
            return
        logger.info("Submitting article...")
        js_submit = """
        (function() {
            try {
                const btns = Array.from(document.querySelectorAll('button')).filter(b => 
                    b.innerText && 
                    b.innerText.trim() === '发布文章' && 
                    b.clientHeight > 0 && 
                    !b.classList.contains('btn-cancel') && 
                    !b.classList.contains('btn-outline')
                );
                
                let submitBtn = null;
                // The correct button is in the popped-up article configuration window.
                for (let i = btns.length - 1; i >= 0; i--) {
                    const btn = btns[i];
                    if (btn.classList.contains('el-button--primary') || btn.closest('.el-dialog') || btn.closest('.modal-box') || btn.closest('[role="dialog"]')) {
                        submitBtn = btn;
                        break;
                    }
                }
                
                // Fallback to the last visible button
                if (!submitBtn && btns.length > 0) {
                    submitBtn = btns[btns.length - 1];
                }
                
                if (submitBtn) {
                    submitBtn.click();
                    const evt = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                    submitBtn.dispatchEvent(evt);
                    return JSON.stringify({ action: "Found submit button in dialog", is_done: true });
                }
                return JSON.stringify({ action: "Submit button not found", is_done: false });
            } catch (err) {
                return JSON.stringify({ error: err.message, is_done: false });
            }
        })();
        """
        res_submit = self.chrome.execute_javascript(w_idx, t_idx, js_submit, settle_seconds=2.0)
        logger.info(f"Publish final result: {res_submit}")

