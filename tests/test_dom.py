import json
from chrome import ChromeDomController

system_chrome = ChromeDomController()
w_idx, t_idx = system_chrome.find_global_tab(["https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit"])

js_code = """
(function() {
    try {
        let editor = document.querySelector('.ProseMirror');
        if (!editor) return "Editor not found";
        
        // Find ProseMirror view
        let view = null;
        for (let key in editor) {
            if (key.startsWith('__pmView')) {
                view = editor[key];
                break;
            }
        }
        
        if (view) {
            return "Found pmView! state.doc.nodeSize: " + view.state.doc.nodeSize;
        } else {
            return "pmView not found on editor node";
        }
    } catch(e) {
        return e.message;
    }
})();
"""
res = system_chrome.execute_javascript(w_idx, t_idx, js_code)
print(f"ProseMirror test result: {res}")
