import time
import json
import pathlib
from loguru import logger
from ..core.jxa_chrome import JxaChromeController

class WechatChannelsPublisher:
    def __init__(self):
        self.chrome = JxaChromeController()

    def publish(self, article_data: dict) -> None:
        title = article_data.get("title", "")
        desc = article_data.get("desc", "")
        video_path = article_data.get("video_path")
        
        if not video_path:
            logger.error("No video_path provided in article_data. Cannot publish to WeChat Channels.")
            return

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["channels.weixin.qq.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
            logger.info(f"Found WeChat Channels Creator Studio tab: {url}")
        except Exception as e:
            logger.warning(f"WeChat Channels tab not found. Creating a new tab: {e}")
            w_idx, t_idx = self.chrome.create_tab("https://channels.weixin.qq.com/platform/post/create")
            time.sleep(5)
            
        url = self.chrome.get_tab_url(w_idx, t_idx)
        if "post/create" not in url:
            new_url = "https://channels.weixin.qq.com/platform/post/create"
            logger.info(f"Navigating to upload page: {new_url}")
            self.chrome.set_tab_url(w_idx, t_idx, new_url, settle_seconds=5.0)
            
        logger.info("Setting up video upload...")
        
        js_click_upload = """
        (function() {
            const btn = document.querySelector('.upload-btn-wrap') || document.querySelector('.weui-desktop-btn_primary');
            if (btn) btn.click();
        })();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_click_upload)
        time.sleep(2)
        
        # AppleScript to interact with macOS file open dialog
        abs_path = pathlib.Path(video_path).absolute()
        dialog_body = f'''
            keystroke "g" using {{command down, shift down}}
            delay 1.0
            keystroke "{abs_path}"
            delay 1.0
            keystroke return
            delay 1.0
            keystroke return
        '''
        self.chrome.run_in_chrome_process(dialog_body)
        logger.info("Initiated file selection dialog.")
        
        # Wait for form to appear
        time.sleep(5)
        
        # Fill details
        js_fill_details = f"""
        (function() {{
            try {{
                const setReactValue = (element, value) => {{
                    element.focus();
                    let lastValue = element.value;
                    element.value = value;
                    let event = new Event('input', {{ bubbles: true }});
                    event.simulated = true;
                    let tracker = element._valueTracker;
                    if (tracker) {{
                        tracker.setValue(lastValue);
                    }}
                    element.dispatchEvent(event);
                }};
                
                const title = {json.dumps(title)};
                const desc = {json.dumps(desc)};
                
                // Description field in WeChat channels usually contains the hashtag and text
                const descInput = document.querySelector('.post-create-desc-textarea, .post-desc-wrapper textarea, [placeholder*="描述"]');
                if (descInput) setReactValue(descInput, title + "\\n" + desc);
                
                // Original setting
                const originalCheck = document.querySelector('.original-statement-checkbox, [aria-label*="原创"]');
                if (originalCheck && !originalCheck.checked) originalCheck.click();
                
                return "Filled metadata";
            }} catch(e) {{
                return e.message;
            }}
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_details)
        logger.info("Filled WeChat Channels video details.")
        
        logger.info("WeChat Channels publishing automation complete. Please verify and submit manually.")
