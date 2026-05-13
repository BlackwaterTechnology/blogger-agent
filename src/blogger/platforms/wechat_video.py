import time
import json
import subprocess
from pathlib import Path
from loguru import logger
from ..core.jxa_chrome import JxaChromeController

class WechatVideoPublisher:
    def __init__(self):
        self.chrome = JxaChromeController()

    def run_ui_state_machine(self, name, w_idx, t_idx, js_code, max_steps=15, delay=1.5):
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
        video_path_raw = article_data.get("video_path")
        if not video_path_raw:
            payload_path = article_data.get("payload_path")
            if payload_path:
                payload_dir = Path(payload_path).parent
                mp4s = list(payload_dir.glob("*.mp4"))
                if mp4s:
                    video_path_raw = mp4s[0]
                    logger.info(f"Auto-detected video file: {video_path_raw}")

        if not video_path_raw:
            raise ValueError("No video file found to publish.")

        video_path = Path(video_path_raw)
        title = article_data.get("title", video_path.stem)
        desc = article_data.get("desc", "")
        cover_path_raw = article_data.get("cover_path")
        cover_path = Path(cover_path_raw) if cover_path_raw else None

        if not video_path or not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://mp.weixin.qq.com"])
        except Exception as e:
            raise SystemExit(f"WeChat tab not found: {e}")
            
        # 1. Upload Video (if not already uploaded)
        js_check_uploaded = "!!document.querySelector('.video-setting__footer-btns-group')"
        if self.chrome.execute_javascript(w_idx, t_idx, js_check_uploaded) != "true":
            logger.info("Triggering video upload...")
            self._click_element_by_text(w_idx, t_idx, ["Upload your video", "上传视频"])
            time.sleep(2)
            self._handle_macos_file_picker(video_path)
            time.sleep(5)

        # 2. Base Metadata
        js_fill_base = f"""
        (function() {{
            try {{
                const title = {json.dumps(title)};
                const desc = {json.dumps(desc)};
                let state = {{ title_filled: false }};
                const labels = Array.from(document.querySelectorAll('.weui-desktop-form__label'));
                
                const tLabel = labels.find(l => l.innerText.includes('Title') || l.innerText.includes('标题'));
                if (tLabel) {{
                    const input = tLabel.closest('.weui-desktop-form__control-group').querySelector('input');
                    if (input) {{ input.focus(); input.value = title; input.dispatchEvent(new Event('input', {{ bubbles: true }})); state.title_filled = true; }}
                }}
                
                const dLabel = labels.find(l => l.innerText.includes('Brief') || l.innerText.includes('简介'));
                if (dLabel) {{
                    const ta = dLabel.closest('.weui-desktop-form__control-group').querySelector('textarea');
                    if (ta) {{ ta.focus(); ta.value = desc; ta.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
                }}
                
                const agree = Array.from(document.querySelectorAll('input[type="checkbox"]')).find(c => c.parentElement.innerText.includes('agree') || c.parentElement.innerText.includes('同意'));
                if (agree && !agree.checked) agree.click();
                
                return JSON.stringify({{state: state, is_done: state.title_filled}});
            }} catch(e) {{ return JSON.stringify({{action: "Error: " + e.toString()}}); }}
        }})()
        """
        self.run_ui_state_machine("Base Metadata", w_idx, t_idx, js_fill_base, max_steps=5)

        # 3. Cover Flow
        self._handle_cover_flow(w_idx, t_idx, cover_path)

        # 4. Originality
        logger.info("Enabling Statement of Originality...")
        self._click_element_by_selector(w_idx, t_idx, ".weui-desktop-switch")
        time.sleep(2)
        # Handle the confirmation dialog
        self._click_element_by_text(w_idx, t_idx, ["Confirm", "确定", "OK"], only_visible=True)
        time.sleep(2)
        
        # 5. Save
        logger.info("Final Save...")
        self._click_element_by_text(w_idx, t_idx, ["Save", "保存"], only_visible=True, skip_disabled=True)

    def _click_element_by_text(self, w_idx, t_idx, texts, only_visible=False, skip_disabled=False):
        texts_json = json.dumps(texts)
        js = f"""
        (function() {{
            const texts = {texts_json};
            const btn = Array.from(document.querySelectorAll("button, a, .weui-desktop-btn")).find(el => {{
                const t = el.innerText.trim();
                const rect = el.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0;
                const isDisabled = el.classList.contains('weui-desktop-btn_disabled') || el.disabled;
                return texts.some(target => t.includes(target)) && (!{str(only_visible).lower()} || isVisible) && (!{str(skip_disabled).lower()} || !isDisabled);
            }});
            if (!btn) return "NOT_FOUND";
            btn.scrollIntoView();
            const r = btn.getBoundingClientRect();
            return JSON.stringify({{ x: r.left + r.width/2, y: r.top + r.height/2, screenX: window.screenX, screenY: window.screenY, toolbarHeight: window.outerHeight - window.innerHeight }});
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js)
        if "NOT_FOUND" not in res:
            geom = json.loads(res)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(geom['screenX']+geom['x'])},{int(geom['screenY']+geom['toolbarHeight']+geom['y'])}"], check=True)
            return True
        return False

    def _click_element_by_selector(self, w_idx, t_idx, selector):
        js = f"""
        (function() {{
            const el = document.querySelector("{selector}");
            if (!el) return "NOT_FOUND";
            el.scrollIntoView();
            const r = el.getBoundingClientRect();
            return JSON.stringify({{ x: r.left + r.width/2, y: r.top + r.height/2, screenX: window.screenX, screenY: window.screenY, toolbarHeight: window.outerHeight - window.innerHeight }});
        }})()
        """
        res = self.chrome.execute_javascript(w_idx, t_idx, js)
        if "NOT_FOUND" not in res:
            geom = json.loads(res)
            subprocess.run(["peekaboo", "click", "--coords", f"{int(geom['screenX']+geom['x'])},{int(geom['screenY']+geom['toolbarHeight']+geom['y'])}"], check=True)
            return True
        return False

    def _handle_macos_file_picker(self, file_path: Path):
        subprocess.run(["peekaboo", "app", "switch", "--to", "Google Chrome"], capture_output=True)
        time.sleep(1)
        subprocess.run(["peekaboo", "hotkey", "command+shift+g"], check=True)
        time.sleep(2)
        subprocess.run(["peekaboo", "type", str(file_path.absolute())], check=True)
        time.sleep(1)
        subprocess.run(["peekaboo", "press", "return"], check=True) # Confirm Path
        time.sleep(2)
        subprocess.run(["peekaboo", "press", "return"], check=True) # Select in list
        time.sleep(1)
        subprocess.run(["peekaboo", "press", "return"], check=True) # Open
        time.sleep(2)

    def _handle_cover_flow(self, w_idx, t_idx, cover_path):
        logger.info("Starting Cover flow...")
        # 1. Open Picker
        if not self._click_element_by_selector(w_idx, t_idx, ".cover__options__item_empty"):
            return
        time.sleep(3)
        
        # 2. Upload file
        if self._click_element_by_text(w_idx, t_idx, ["Upload file", "上传图片"]):
            time.sleep(2)
            self._handle_macos_file_picker(cover_path or Path("videos/notebooklm_auth_modes/cover.png"))
            time.sleep(5)
            
        # 3. Select first image & Click Next
        js_select_and_next = """
        (function() {
            const imgs = document.querySelectorAll(".weui-desktop-img-picker__img_thumb, .img_pick img, .img_item_bd img, .cover__options__item__image");
            if (imgs.length > 0) imgs[0].click();
            setTimeout(() => {
                const next = Array.from(document.querySelectorAll("button")).find(b => b.innerText.includes("Next") || b.innerText.includes("下一步"));
                if (next) next.click();
            }, 1000);
        })()
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_select_and_next)
        time.sleep(4)
        
        # 4. Done
        self._click_element_by_text(w_idx, t_idx, ["Done", "完成"], only_visible=True)
        time.sleep(2)
