import time
import json
from loguru import logger
from ..core.cdp_chrome import CdpChromeController

class BilibiliPublisher:
    def __init__(self):
        self.chrome = CdpChromeController()

    def publish(self, article_data: dict, *, dry_run: bool = False) -> None:
        title = article_data.get("title", "")
        desc = article_data.get("desc", "")
        collection = article_data.get("collection", "Tech/AI")
        video_path = article_data.get("video_path")
        cover_path = article_data.get("cover_path")
        
        if not video_path:
            logger.error("No video_path provided.")
            return

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["https://member.bilibili.com/platform/upload/video"])
        except Exception:
            raise SystemExit("Bilibili upload tab not found. Please open the upload page and retry.")

        logger.info(f"Uploading video: {video_path}")
        self.chrome.set_file_input(t_idx, 'input[type="file"]', video_path)

        # Wait for form to load
        logger.info("Waiting for upload form to appear...")
        js_wait_form = """
        (function() {
            return !!document.querySelector('.video-title .input-val');
        })();
        """
        form_found = False
        for _ in range(30):
            res = self.chrome.execute_javascript(w_idx, t_idx, js_wait_form)
            if res == "True" or res == "true":
                form_found = True
                break
            time.sleep(1.0)
            
        if not form_found:
            logger.error("Upload form did not appear after 30 seconds. Video may still be processing or selector changed.")
            return
