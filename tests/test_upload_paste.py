import json
import time
from chrome import ChromeDomController

system_chrome = ChromeDomController()
w_idx, t_idx = system_chrome.find_global_tab(["https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit"])

# Move cursor to before the first heading
js_move_cursor = """
(function() {
    try {
        let editor = document.querySelector('.ProseMirror');
        if (!editor) return "Editor not found";
        
        editor.focus();
        const selection = window.getSelection();
        const range = document.createRange();
        
        const h1 = editor.querySelector('h1, h2, h3');
        if (h1) {
            range.setStartBefore(h1);
            range.collapse(true);
        } else {
            range.selectNodeContents(editor);
            range.collapse(true);
        }
        
        selection.removeAllRanges();
        selection.addRange(range);
        return "Cursor moved";
    } catch(e) {
        return e.message;
    }
})();
"""
res = system_chrome.execute_javascript(w_idx, t_idx, js_move_cursor)
print(f"Cursor move: {res}")

time.sleep(0.5)

# Trigger Cmd+V using AppleScript
trigger_paste = '''
tell application "System Events"
    tell process "Google Chrome"
        set frontmost to true
        keystroke "v" using {command down}
    end tell
end tell
'''
res2 = system_chrome._run_osascript(trigger_paste)
print(f"Paste result: {res2}")

time.sleep(2.0)

# Check for images in the editor
js_check_images = """
(function() {
    const editor = document.querySelector('.ProseMirror');
    if (!editor) return "No editor";
    const imgs = Array.from(editor.querySelectorAll('img'));
    return JSON.stringify(imgs.map(i => i.src));
})();
"""
res3 = system_chrome.execute_javascript(w_idx, t_idx, js_check_images)
print(f"Images in editor: {res3}")
