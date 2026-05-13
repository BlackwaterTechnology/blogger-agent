import time
import json
import subprocess
import urllib.parse
from pathlib import Path
from loguru import logger
from ..core.jxa_chrome import JxaChromeController

class WechatVideoPublisher:
    def __init__(self):
        self.chrome = JxaChromeController()

    def publish(self, article_data: dict) -> None:
        video_path_raw = article_data.get("video_path")
        if not video_path_raw:
            payload_path = article_data.get("payload_path")
            if payload_path:
                payload_dir = Path(payload_path).parent
                mp4s = list(payload_dir.glob("*.mp4"))
                if mp4s: video_path_raw = mp4s[0]
        
        if not video_path_raw: raise ValueError("No video file found.")
        video_path = Path(video_path_raw)
        title = article_data.get("title", video_path.stem)
        desc = article_data.get("desc", "")
        collection = article_data.get("collection", "AI")
        cover_path_raw = article_data.get("cover_path")
        cover_path = Path(cover_path_raw) if cover_path_raw else None

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
        except Exception as e: raise SystemExit(f"WeChat tab not found: {e}")

        if "videomsg_edit" not in url and "action=list_video" not in url and "action=edit" not in url:
            parsed = urllib.parse.urlparse(url)
            token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
            if token:
                target = f"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/videomsg_edit&action=video_edit&type=15&token={token}&lang=en_US"
                self.chrome.set_tab_url(w_idx, t_idx, target, settle_seconds=5.0)
                url = target

        if "t=media/videomsg_edit" in url:
            if self._handle_initial_upload(w_idx, t_idx, video_path, title, desc, cover_path):
                time.sleep(5)
                try:
                    w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit"])
                    url = self.chrome.get_tab_url(w_idx, t_idx)
                except: pass
            else:
                time.sleep(5)
                w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
                url = self.chrome.get_tab_url(w_idx, t_idx)

        if "action=list_video" in url:
            self._handle_library_page(w_idx, t_idx, title)
            time.sleep(6)
            w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit"])
            url = self.chrome.get_tab_url(w_idx, t_idx)

        if "action=edit" in url:
            self._handle_final_publish_settings(w_idx, t_idx, desc, collection)

    def _handle_initial_upload(self, w_idx, t_idx, video_path, title, desc, cover_path):
        logger.info("Handling Initial Upload...")
        if self.chrome.execute_javascript(w_idx, t_idx, "!!document.querySelector('.video-setting__footer-btns-group')") != "true":
            self._click_upload_button(w_idx, t_idx)
            time.sleep(3)
            self._handle_macos_file_picker(video_path)
            time.sleep(5)
        
        js_base = f"""
        (function() {{
            const labels = Array.from(document.querySelectorAll('.weui-desktop-form__label'));
            const tLabel = labels.find(l => l.innerText.includes('Title') || l.innerText.includes('标题'));
            if (tLabel) {{
                const input = tLabel.closest('.weui-desktop-form__control-group').querySelector('input');
                if (input) {{ input.focus(); input.value = {json.dumps(title)}; input.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
            }}
            const sw = document.querySelector('input.weui-desktop-switch__input');
            if (sw && !sw.checked) sw.click();
            const agree = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(c => c.parentElement.innerText.includes('agree') || c.parentElement.innerText.includes('同意'));
            if (agree && !agree.checked) agree.click();
            return "DONE";
        }})()
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_base)
        time.sleep(2)
        self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定", "OK"], only_visible=True)
        time.sleep(2)
        self._handle_cover_flow(w_idx, t_idx, cover_path)
        
        for _ in range(10):
            if self._click_element_by_text(w_idx, t_idx, ["Save and Publish", "保存并发表"], only_visible=True, skip_disabled=True):
                return True
            time.sleep(3)
        self._click_element_by_text(w_idx, t_idx, ["Save", "保存"], only_visible=True, skip_disabled=True)
        return False

    def _handle_final_publish_settings(self, w_idx, t_idx, desc, collection):
        logger.info("Executing Final Publishing Settings...")
        # 1. Fill Description
        js_desc = f"""
        (function() {{
            const editor = document.querySelector(".ProseMirror");
            if (editor) {{
                editor.focus();
                document.execCommand("selectAll", false, null);
                document.execCommand("delete", false, null);
                document.execCommand("insertText", false, {json.dumps(desc)});
            }}
        }})()
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_desc)
        self.chrome.execute_javascript(w_idx, t_idx, "window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # 2. Reward & Comments
        for selector in [".js_reward_allow_click_cell", ".js_interaction_cell"]:
            if self._click_element_by_selector(w_idx, t_idx, selector):
                time.sleep(2)
                # Toggle switch in dialog if not checked
                js_toggle = "const sw = document.querySelector('.weui-desktop-dialog .weui-desktop-switch__input'); if(sw && !sw.checked) sw.click();"
                self.chrome.execute_javascript(w_idx, t_idx, js_toggle)
                time.sleep(1)
                self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定"], only_visible=True)
                time.sleep(1)

        # 3. Collection
        logger.info(f"Setting collection: {collection}")
        if self._click_element_by_selector(w_idx, t_idx, ".js_article_tags_label"):
            time.sleep(2)
            # Focus and type
            js_focus = "const i = Array.from(document.querySelectorAll('input')).find(inp => inp.placeholder.includes('Collection') && inp.getBoundingClientRect().width > 0); if(i) { i.focus(); i.value = ''; }"
            self.chrome.execute_javascript(w_idx, t_idx, js_focus)
            subprocess.run(["peekaboo", "type", collection], check=True)
            time.sleep(2)
            # Click Suggestion
            js_sug = f"""
            (function() {{
                const els = Array.from(document.querySelectorAll("*")).filter(el => (el.innerText || "").trim().toLowerCase() === {json.dumps(collection.lower())} && el.getBoundingClientRect().width > 0);
                if (els.length === 0) return "NOT_FOUND";
                const r = els[els.length-1].getBoundingClientRect();
                return JSON.stringify({{ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight }});
            }})()
            """
            s_res = self.chrome.execute_javascript(w_idx, t_idx, js_sug)
            if "NOT_FOUND" not in s_res:
                g = json.loads(s_res)
                subprocess.run(["peekaboo", "click", "--coords", f"{int(g['sx']+g['x'])},{int(g['sy']+g['th']+g['y'])}"], check=True)
                time.sleep(1)
            self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定"], only_visible=True)

        # 4. Creation Source
        if self._click_element_by_selector(w_idx, t_idx, ".js_claim_source_desc"):
            time.sleep(2)
            self._click_element_by_text(w_idx, t_idx, ["个人观点"], only_visible=True)
            time.sleep(1)
            self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定"], only_visible=True)

        # 5. Final Save
        time.sleep(2)
        self._click_element_by_text(w_idx, t_idx, ["Save as draft", "保存草稿"], only_visible=True)
        logger.info("Publish flow completed.")

    def _click_upload_button(self, w_idx, t_idx):
        js = """
        (function() {
            const btn = Array.from(document.querySelectorAll("button, a")).find(b => b.innerText.includes("Upload your video") || b.innerText.includes("上传视频"));
            if (!btn) return "NOT_FOUND";
            const r = btn.getBoundingClientRect();
            return JSON.stringify({ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight });
        })()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js)
        if "NOT_FOUND" not in res:
            g = json.loads(res)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(g['sx']+g['x'])},{int(g['sy']+g['th']+g['y'])}"], check=True)

    def _click_element_by_text(self, w_idx, t_idx, texts, only_visible=False, skip_disabled=False):
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

    def _click_element_by_selector(self, w_idx, t_idx, selector):
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
        subprocess.run(["peekaboo", "app", "switch", "--to", "Google Chrome"], capture_output=True)
        time.sleep(1); subprocess.run(["peekaboo", "hotkey", "command+shift+g"], check=True)
        time.sleep(1.5); subprocess.run(["peekaboo", "type", str(file_path.absolute())], check=True)
        time.sleep(1); subprocess.run(["peekaboo", "press", "return"], check=True)
        time.sleep(1.5); subprocess.run(["peekaboo", "press", "return"], check=True)
        time.sleep(1); subprocess.run(["peekaboo", "press", "return"], check=True)
        time.sleep(2)

    def _handle_cover_flow(self, w_idx, t_idx, cover_path):
        logger.info("Starting Cover flow...")
        if not self._click_element_by_selector(w_idx, t_idx, ".cover__options__item_empty"): return
        time.sleep(3)
        if self._click_element_by_text(w_idx, t_idx, ["Upload file", "上传图片"]):
            time.sleep(2)
            self._handle_macos_file_picker(cover_path or Path("videos/notebooklm_auth_modes/cover.png"))
            time.sleep(5)
        js_select = """
        (function() {
            const imgs = document.querySelectorAll(".weui-desktop-img-picker__img_thumb, .img_pick img, .img_item_bd img, .cover__options__item__image");
            if (imgs.length === 0) return "NOT_FOUND";
            const r = imgs[0].getBoundingClientRect();
            return JSON.stringify({ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight });
        })()
        """
        res_i = self.chrome.execute_javascript(w_idx, t_idx, js_select)
        if "NOT_FOUND" not in res_i:
            g = json.loads(res_i)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(g['sx']+g['x'])},{int(g['sy']+g['th']+g['y'])}"], check=True)
            time.sleep(1.5)
            self._click_element_by_text(w_idx, t_idx, ["Next", "下一步"])
            time.sleep(4)
            self._click_element_by_text(w_idx, t_idx, ["Done", "完成"], only_visible=True)
            time.sleep(2)

    def _handle_library_page(self, w_idx, t_idx, title):
        logger.info("Navigating Content Library...")
        js_find = f"""
        (function() {{
            const rows = Array.from(document.querySelectorAll("tr, .weui-desktop-media-list__item"));
            const row = rows.find(r => r.innerText.includes({json.dumps(title[:20])}));
            if (!row) return "ROW_NOT_FOUND";
            const btn = row.querySelector("a.weui-desktop-icon-btn");
            const r = btn.getBoundingClientRect();
            return JSON.stringify({{ x: r.left + r.width/2, y: r.top + r.height/2, sx: window.screenX, sy: window.screenY, th: window.outerHeight - window.innerHeight }});
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js_find)
        if "NOT_FOUND" not in res:
            g = json.loads(res)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(g['sx']+g['x'])},{int(g['sy']+g['th']+g['y'])}"], check=True)
