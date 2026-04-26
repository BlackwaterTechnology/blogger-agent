import json
from chrome import ChromeDomController

system_chrome = ChromeDomController()
try:
    w_idx, t_idx = system_chrome.find_global_tab(["https://mp.weixin.qq.com"])
    js_check_images = """
    (function() {
        const editor = document.querySelector('.ProseMirror');
        if (!editor) return "No editor";
        const imgs = Array.from(editor.querySelectorAll('img'));
        return JSON.stringify(imgs.map(i => i.src));
    })();
    """
    res = system_chrome.execute_javascript(w_idx, t_idx, js_check_images)
    print(f"Images in editor: {res}")
except Exception as e:
    print(f"Error: {e}")
