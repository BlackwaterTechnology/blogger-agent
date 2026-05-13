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
            w_idx, t_idx = self.chrome.find_global_tab(["https://member.bilibili.com/platform/upload/video/frame"])
        except Exception:
            raise SystemExit("Bilibili upload tab not found. Please open the upload page and retry.")
