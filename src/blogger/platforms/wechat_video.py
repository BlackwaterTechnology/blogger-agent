import time
import json
import subprocess
import urllib.parse
from pathlib import Path
from loguru import logger
from ..core.jxa_chrome import JxaChromeController
from ..config import get_wechat_collections

class WechatVideoPublisher:
    def __init__(self):
        self.chrome = JxaChromeController()

    def publish(self, article_data: dict) -> None:
        # 1. Prepare Data
        video_path_raw = article_data.get("video_path")
        if not video_path_raw:
            payload_path = article_data.get("payload_path")
            if payload_path:
                payload_dir = Path(payload_path)
                if payload_dir.is_file():
                    payload_dir = payload_dir.parent
                    
                # Prioritize watermark-removed video
                clean_mp4s = list(payload_dir.glob("*_clean.mp4"))
                if clean_mp4s:
                    video_path_raw = clean_mp4s[0]
                else:
                    mp4s = list(payload_dir.glob("*.mp4"))
                    if mp4s: video_path_raw = mp4s[0]
        
        if not video_path_raw: raise ValueError("No video file found.")
        video_path = Path(video_path_raw)
        title = article_data.get("title", video_path.stem)
        desc = article_data.get("desc", "")
        
        # Validate Collection against config
        allowed_collections = get_wechat_collections(content_type="video")
        collection = article_data.get("collection", "agent")
        if collection not in allowed_collections:
            logger.warning(f"Collection '{collection}' not in allowed video_collections {allowed_collections}. Defaulting to '{allowed_collections[0]}' if available.")
            if allowed_collections:
                collection = allowed_collections[0]

        cover_path_raw = article_data.get("cover_path")
        if not cover_path_raw:
            payload_path = article_data.get("payload_path")
            if payload_path:
                payload_dir = Path(payload_path)
                if payload_dir.is_file():
                    payload_dir = payload_dir.parent
                potential_cover = payload_dir / "cover.png"
                if potential_cover.exists():
                    cover_path_raw = str(potential_cover)

        cover_path = Path(cover_path_raw) if cover_path_raw else None

        try:
            # First try finding an existing video upload or video edit tab
            try:
                w_idx, t_idx = self.chrome.find_global_tab(["videomsg_edit"])
            except Exception:
                try:
                    w_idx, t_idx = self.chrome.find_global_tab(["material_type=15"])
                except Exception:
                    w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
            logger.info(f"Connected to WeChat: {url}")
        except Exception as e: raise SystemExit(f"WeChat tab not found: {e}")

        # 0. Check if already on a video upload or video edit page
        is_video_upload = "videomsg_edit" in url or "action=video_edit" in url
        is_video_list = "action=list_video" in url
        is_video_final_edit = "action=edit" in url and ("material_type=15" in url or "type=15" in url)

        # If on an article editor or generic home page, redirect to video upload page
        if not (is_video_upload or is_video_list or is_video_final_edit):
            logger.info("Current tab is not a video page. Redirecting to video upload page...")
            parsed = urllib.parse.urlparse(url)
            token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
            if token:
                target = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/videomsg_edit&action=video_edit&type=15&token={token}&lang=en_US"
                # If on an article editor, create a fresh tab to avoid triggering window.onbeforeunload
                if "action=edit" in url or "appmsg_edit" in url:
                    old_w, old_t = w_idx, t_idx
                    w_idx, t_idx = self.chrome.create_tab(target)
                    time.sleep(3)
                    try:
                        self.chrome.close_tab(old_w, old_t)
                    except Exception:
                        pass
                else:
                    self.chrome.set_tab_url(w_idx, t_idx, target, settle_seconds=5.0)
                time.sleep(3)
                url = self.chrome.get_tab_url(w_idx, t_idx)

        # 1. Stage: Initial Upload
        if "videomsg_edit" in url or "action=video_edit" in url:
            logger.info("Entering Upload Stage...")
            success_jump = self._handle_initial_upload(w_idx, t_idx, video_path, title, desc, cover_path)
            if success_jump:
                time.sleep(6) # Wait for new tab or redirect
                try:
                    w_idx, t_idx = self.chrome.find_global_tab(["material_type=15"])
                    url = self.chrome.get_tab_url(w_idx, t_idx)
                except Exception:
                    try:
                        w_idx, t_idx = self.chrome.find_global_tab(["action=list_video"])
                        url = self.chrome.get_tab_url(w_idx, t_idx)
                    except Exception:
                        pass
            else:
                time.sleep(3)
                try:
                    w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
                    url = self.chrome.get_tab_url(w_idx, t_idx)
                except Exception:
                    pass

        # 2. Stage: Library fallback
        if "action=list_video" in url:
            logger.info("Entering Library Stage...")
            self._handle_library_page(w_idx, t_idx, title)
            time.sleep(6)
            try:
                w_idx, t_idx = self.chrome.find_global_tab(["material_type=15"])
                url = self.chrome.get_tab_url(w_idx, t_idx)
            except Exception:
                pass

        # 3. Stage: Final Edit (strictly requires video type=15 / material_type=15)
        if "action=edit" in url and ("material_type=15" in url or "type=15" in url):
            logger.info("Entering Final Edit Stage...")
            self._handle_final_publish_settings(w_idx, t_idx, desc, collection)
        elif "action=edit" in url:
            logger.warning(f"Aborted: Tab is an article editor, not a video editor! URL: {url}")
        else:
            logger.warning(f"Flow paused. Please ensure you are on the video editor page. URL: {url}")

    def _handle_initial_upload(self, w_idx, t_idx, video_path, title, desc, cover_path):
        js_needs_upload = """
        (function() {
            const btn = Array.from(document.querySelectorAll("button, a, .weui-desktop-btn")).find(b => {
                const t = b.innerText.trim();
                return (t === "Upload your video" || t === "上传视频" || t.includes("Upload your video") || t.includes("上传视频")) && b.getBoundingClientRect().width > 0;
            });
            return !!btn;
        })()
        """
        if self.chrome.execute_javascript(w_idx, t_idx, js_needs_upload) == "true":
            logger.info(f"Triggering video file upload: {video_path}")
            self._click_upload_button(w_idx, t_idx)
            time.sleep(2.5)
            self._handle_macos_file_picker(video_path)
            
            logger.info("Waiting for video upload to process...")
            for _ in range(40):
                time.sleep(2.0)
                js_check = """
                (function() {
                    const prog = document.querySelector('.weui-desktop-upload__file__progress, .weui-desktop-progress');
                    if (prog && prog.offsetParent !== null) {
                        const txt = (prog.innerText || "").trim();
                        if (txt === "100%") return "DONE";
                        return "UPLOADING";
                    }
                    const btn = Array.from(document.querySelectorAll("button, a, .weui-desktop-btn")).find(b => {
                        const t = b.innerText.trim();
                        return (t === "Upload your video" || t === "上传视频") && b.getBoundingClientRect().width > 0;
                    });
                    return btn ? "STILL_BTN" : "DONE";
                })()
                """
                res = self.chrome.execute_javascript(w_idx, t_idx, js_check)
                if res == "DONE":
                    logger.info("Video uploaded successfully.")
                    break
                elif res == "UPLOADING":
                    logger.debug("Video upload in progress...")
        
        js_base = f"""
        (function() {{
            const labels = Array.from(document.querySelectorAll('.weui-desktop-form__label'));
            const tLabel = labels.find(l => l.innerText.includes('Title') || l.innerText.includes('标题'));
            if (tLabel) {{
                const input = tLabel.closest('.weui-desktop-form__control-group').querySelector('input');
                if (input) {{
                    input.focus();
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    if (setter) {{ setter.call(input, {json.dumps(title)}); }} else {{ input.value = {json.dumps(title)}; }}
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
            const agree = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(c => 
                (c.parentElement && (c.parentElement.innerText || "").includes("I have read and agreed")) ||
                (c.closest("label") && (c.closest("label").innerText || "").includes("I have read and agreed")) ||
                (c.parentElement && (c.parentElement.innerText || "").includes("agree")) ||
                (c.parentElement && (c.parentElement.innerText || "").includes("同意"))
            );
            if (agree && !agree.checked) agree.click();
            return "DONE";
        }})()
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_base)
        time.sleep(1.5)
        
        # Originality Switch
        js_sw = """
        (function() {
            const swLabel = document.querySelector(".weui-desktop-switch");
            if (swLabel) swLabel.click();
        })()
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_sw)
        time.sleep(1.5)
        self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定", "OK"], "Confirming Originality Modal", only_visible=True)
        time.sleep(1.5)
        
        # Cover upload
        self._handle_cover_flow(w_idx, t_idx, cover_path)
        
        logger.info("Waiting for 'Save and Publish'...")
        for _ in range(12):
            if self._click_element_by_text(w_idx, t_idx, ["Save and Publish", "保存并发表"], "Clicking 'Save and Publish'", only_visible=True, skip_disabled=True):
                time.sleep(2)
                # Handle possible confirmation warning modal ("Submit video: The video has not declared originality")
                self._click_element_by_text(w_idx, t_idx, ["Continue submission", "继续提交"], "Confirming submission dialog", only_visible=True)
                return True
            time.sleep(3)
        self._click_element_by_text(w_idx, t_idx, ["Save", "保存"], "Falling back to 'Save'", only_visible=True, skip_disabled=True)
        return False

    def _handle_final_publish_settings(self, w_idx, t_idx, desc, collection):
        # 1. Fill Description into ProseMirror
        if desc:
            html_body = f"<p>{desc}</p>"
            js_desc = f"""
            (function() {{
                const descEl = document.querySelector(".ProseMirror");
                if (descEl) {{
                    descEl.focus();
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(descEl);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    document.execCommand("delete", false, null);
                    descEl.innerHTML = {json.dumps(html_body)};
                    descEl.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    descEl.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    return "DONE";
                }}
                return "NO_EDITOR";
            }})()
            """
            self.chrome.execute_javascript(w_idx, t_idx, js_desc)
        
        self.chrome.execute_javascript(w_idx, t_idx, "window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # 2. Reward & Comments
        for selector, label in [(".js_reward_allow_click_cell", "Reward"), (".js_interaction_cell", "Comments")]:
            if self._click_element_by_selector(w_idx, t_idx, selector, f"Opening {label} settings"):
                time.sleep(2)
                js_toggle = "document.querySelectorAll('.weui-desktop-dialog .weui-desktop-switch__input').forEach(sw => { if(!sw.checked) sw.click(); });"
                self.chrome.execute_javascript(w_idx, t_idx, js_toggle)
                time.sleep(1)
                self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定"], f"Confirming {label} settings", only_visible=True)
                time.sleep(1)

        # 3. Collection
        if collection:
            logger.info(f"Setting collection: {collection}")
            if self._click_element_by_selector(w_idx, t_idx, ".js_article_tags_label", "Opening Collection settings"):
                time.sleep(2)
                js_select_col = f"""
                (function() {{
                    const input = Array.from(document.querySelectorAll(".weui-desktop-dialog input")).find(inp => 
                        (inp.placeholder || "").includes("Collection") || (inp.placeholder || "").includes("合集")
                    );
                    if (input) {{ input.focus(); input.click(); }}
                    
                    const items = Array.from(document.querySelectorAll(".select-opt-li, .weui-desktop-dropdown li"));
                    const target = items.find(el => (el.innerText || "").trim().toLowerCase() === {json.dumps(collection.lower())});
                    if (target) {{
                        target.click();
                        return "CLICKED_ITEM";
                    }}
                    return "ITEM_NOT_FOUND";
                }})()
                """
                self.chrome.execute_javascript(w_idx, t_idx, js_select_col)
                time.sleep(1)
                self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定"], "Confirming Collection settings", only_visible=True)
                time.sleep(1)

        # 4. Creation Source
        if self._click_element_by_selector(w_idx, t_idx, ".js_claim_source_desc", "Opening Creation Source settings"):
            time.sleep(2)
            source_labels = ["个人观点", "Personal Opinion", "Original", "创作来源"]
            js_select_source = f"""
            (function() {{
                const targets = {json.dumps(source_labels)};
                const labels = Array.from(document.querySelectorAll(".weui-desktop-dialog label, .weui-desktop-dialog span, .weui-desktop-dialog .weui-desktop-form__check-content"));
                const target = labels.find(el => targets.some(t => (el.innerText || "").includes(t)));
                if (target) {{
                    target.click();
                    return "CLICKED_SOURCE";
                }}
                return "NOT_FOUND";
            }})()
            """
            self.chrome.execute_javascript(w_idx, t_idx, js_select_source)
            time.sleep(1)
            self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定", "OK"], "Confirming Creation Source", only_visible=True)
            time.sleep(1)

        # 5. Final Save
        time.sleep(2)
        self._click_element_by_text(w_idx, t_idx, ["Save as draft", "保存草稿"], "Final Save as Draft", only_visible=True)
        logger.info("Publish flow completed.")

    def _click_upload_button(self, w_idx, t_idx):
        js = """
        (function() {
            const btn = Array.from(document.querySelectorAll("button, a, .weui-desktop-btn")).find(b => {
                const t = b.innerText.trim();
                return (t === "Upload your video" || t === "上传视频" || t.includes("Upload your video") || t.includes("上传视频")) && b.getBoundingClientRect().width > 0;
            });
            if (!btn) return "NOT_FOUND";
            btn.scrollIntoView({block: "center"});
            const r = btn.getBoundingClientRect();
            return JSON.stringify({ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight });
        })()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js)
        if "NOT_FOUND" not in res:
            logger.info("Clicking 'Upload your video' button")
            g = json.loads(res)
            sx, sy = g["sx"] + g["x"], g["sy"] + g["th"] + g["y"]
            subprocess.run(["peekaboo", "app", "switch", "--to", "Google Chrome"], capture_output=True)
            time.sleep(0.5)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(sx)},{int(sy)}"], check=True)

    def _click_element_by_text(self, w_idx, t_idx, texts, action_desc, only_visible=False, skip_disabled=False):
        logger.info(f"Action: {action_desc}")
        js = f"""
        (function() {{
            const texts = {json.dumps(texts)};
            const btns = Array.from(document.querySelectorAll("button, a, .weui-desktop-btn, span, label, .weui-desktop-link")).filter(el => {{
                const t = el.innerText.trim();
                const r = el.getBoundingClientRect();
                const isVis = r.width > 0 && r.height > 0;
                const isDis = el.classList.contains('weui-desktop-btn_disabled') || el.disabled;
                return texts.some(target => t.includes(target)) && (!{str(only_visible).lower()} || isVis) && (!{str(skip_disabled).lower()} || !isDis);
            }});
            if (btns.length === 0) return "NOT_FOUND";
            const btn = btns[btns.length - 1];
            btn.scrollIntoView({{block: "center"}});
            const r = btn.getBoundingClientRect();
            return JSON.stringify({{ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight }});
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js)
        if "NOT_FOUND" not in res:
            g = json.loads(res)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(g['sx']+g['x'])},{int(g['sy']+g['th']+g['y'])}"], check=True)
            return True
        return False

    def _click_element_by_selector(self, w_idx, t_idx, selector, action_desc):
        logger.info(f"Action: {action_desc}")
        js = f"""
        (function() {{
            const el = document.querySelector("{selector}");
            if (!el) return "NOT_FOUND";
            el.scrollIntoView({{block: "center"}});
            const r = el.getBoundingClientRect();
            return JSON.stringify({{ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight }});
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js)
        if "NOT_FOUND" not in res:
            g = json.loads(res)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(g['sx']+g['x'])},{int(g['sy']+g['th']+g['y'])}"], check=True)
            return True
        return False

    def _handle_macos_file_picker(self, file_path: Path):
        subprocess.run(["pbcopy"], input=str(file_path.absolute()).encode("utf-8"), check=True)
        # Use JXA / AppleScript to activate Chrome and paste file path in file chooser
        inner = (
            'keystroke "g" using {command down, shift down}\n'
            'delay 1.0\n'
            'keystroke "a" using {command down}\n'
            'delay 0.2\n'
            'keystroke "v" using {command down}\n'
            'delay 0.5\n'
            'key code 36\n'
            'delay 1.0\n'
            'key code 36\n'
            'delay 0.5\n'
            'key code 36'
        )
        self.chrome.run_in_chrome_process(inner)
        time.sleep(2.0)

    def _handle_cover_flow(self, w_idx, t_idx, cover_path):
        if not cover_path or not Path(cover_path).exists():
            logger.info("No cover specified or file not found, skipping custom cover upload.")
            return

        logger.info(f"Uploading cover image: {cover_path}")
        # 1. Open Picker
        js_open_picker = """
        (function() {
            const item = document.querySelector(".cover__options__item_empty, .cover__options__item_clickable");
            if (item) { item.click(); return "OK"; }
            return "NOT_FOUND";
        })()
        """
        if self.chrome.execute_javascript(w_idx, t_idx, js_open_picker) == "NOT_FOUND":
            logger.warning("Cover picker item not found.")
            return
        time.sleep(2.5)

        # 2. Upload via DataTransfer into file input inside dialog
        import base64
        cover_file = Path(cover_path)
        b64_data = base64.b64encode(cover_file.read_bytes()).decode("utf-8")
        filename = cover_file.name

        js_upload = f"""
        (function() {{
            try {{
                const b64Data = {json.dumps(b64_data)};
                const filename = {json.dumps(filename)};
                const binStr = atob(b64Data);
                const len = binStr.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{ bytes[i] = binStr.charCodeAt(i); }}
                const blob = new Blob([bytes.buffer], {{ type: "image/png" }});
                const file = new File([blob], filename, {{ type: "image/png" }});
                const dt = new DataTransfer();
                dt.items.add(file);
                const targetInput = document.querySelector(".weui-desktop-dialog__wrp.weui-desktop-dialog_img-picker input[type=\\"file\\"]");
                if (!targetInput) return JSON.stringify({{ error: "No target input found" }});
                targetInput.files = dt.files;
                targetInput.dispatchEvent(new Event("change", {{ bubbles: true }}));
                return JSON.stringify({{ success: true }});
            }} catch(e) {{
                return JSON.stringify({{ error: e.message }});
            }}
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_upload)
        logger.info(f"Cover upload result: {res}")
        time.sleep(3.5)

        # 3. Click Next
        js_click_next = """
        (function() {
            const dialog = document.querySelector(".weui-desktop-dialog__wrp.weui-desktop-dialog_img-picker");
            if (!dialog) return "NO_DIALOG";
            const nextBtn = Array.from(dialog.querySelectorAll("button")).find(b => (b.innerText || "").includes("Next") || (b.innerText || "").includes("下一步"));
            if (nextBtn && !nextBtn.disabled && !nextBtn.classList.contains("weui-desktop-btn_disabled")) {
                nextBtn.click();
                return "CLICKED_NEXT";
            }
            return "DISABLED_OR_NOT_FOUND";
        })()
        """
        for _ in range(5):
            if self.chrome.execute_javascript(w_idx, t_idx, js_click_next) == "CLICKED_NEXT":
                break
            time.sleep(1.5)

        time.sleep(2.5)

        # 4. Click Done
        js_click_done = """
        (function() {
            const dialog = document.querySelector(".weui-desktop-dialog__wrp.weui-desktop-dialog_img-picker");
            if (!dialog) return "NO_DIALOG";
            const doneBtn = Array.from(dialog.querySelectorAll("button")).find(b => (b.innerText || "").includes("Done") || (b.innerText || "").includes("完成"));
            if (doneBtn && !doneBtn.disabled && !doneBtn.classList.contains("weui-desktop-btn_disabled")) {
                doneBtn.click();
                return "CLICKED_DONE";
            }
            return "DISABLED_OR_NOT_FOUND";
        })()
        """
        for _ in range(5):
            if self.chrome.execute_javascript(w_idx, t_idx, js_click_done) == "CLICKED_DONE":
                break
            time.sleep(1.5)
        time.sleep(2)

    def _handle_library_page(self, w_idx, t_idx, title):
        js_find = f"""
        (function() {{
            const rows = Array.from(document.querySelectorAll("tr, .weui-desktop-media-list__item"));
            const row = rows.find(r => r.innerText.includes({json.dumps(title[:20])}));
            if (!row) return "ROW_NOT_FOUND";
            const btn = row.querySelector("a.weui-desktop-icon-btn");
            if (!btn) return "BTN_NOT_FOUND";
            btn.click();
            return "CLICKED";
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_find)
        logger.info(f"Clicking publish for video '{title[:20]}': {res}")
