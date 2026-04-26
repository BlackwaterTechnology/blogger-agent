import json
from chrome import ChromeDomController

system_chrome = ChromeDomController()
w_idx, t_idx = system_chrome.find_global_tab(["https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit"])

js_code = """
(function() {
    try {
        let editor = document.querySelector('.ProseMirror');
        if (!editor) return JSON.stringify({error: "Editor not found"});
        
        const imgs = Array.from(editor.querySelectorAll('img'));
        return JSON.stringify({
            imageCount: imgs.length
        }, null, 2);
    } catch(e) {
        return JSON.stringify({error: e.message});
    }
})();
"""
res = system_chrome.execute_javascript(w_idx, t_idx, js_code)
print(f"Check result: {res}")
