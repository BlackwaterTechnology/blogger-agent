import json
import time
from chrome import ChromeDomController
import subprocess

system_chrome = ChromeDomController()
w_idx, t_idx = system_chrome.find_global_tab(["t=media/appmsg_edit"])

def run_applescript(script):
    process = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    return out.decode('utf-8').strip(), err.decode('utf-8').strip()

# 1. Get coordinates of the Image button
js_get_img_btn = """
(function() {
    const imgBtn = document.querySelector('li.tpl_item_dropdown.jsInsertIcon.img');
    if (!imgBtn) return JSON.stringify({error: "Image button not found"});
    const rect = imgBtn.getBoundingClientRect();
    return JSON.stringify({
        x: rect.left + rect.width / 2 + window.screenX, // this might need adjustment based on window position
        y: rect.top + rect.height / 2 + window.screenY + (window.outerHeight - window.innerHeight) // titlebar height
    });
})();
"""

# Wait, calculating absolute screen coordinates from window coordinates in Chrome is tricky because of the toolbar/tabs/bookmarks bar height.
# AppleScript can get the window's position and size.
# Actually, window.screenX and window.screenY give the top-left of the browser window.
# But inner height vs outer height can be used. A more robust way:
