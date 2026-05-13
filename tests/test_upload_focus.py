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

js_focus_input = """
(function() {
    try {
        const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
        if (fileInputs.length === 0) return "No file input";
        
        const input = fileInputs[0];
        
        // Make it focusable and visible enough for the browser to allow focus
        input.style.display = 'block';
        input.style.visibility = 'visible';
        input.style.opacity = '0.01';
        input.style.position = 'fixed';
        input.style.top = '100px';
        input.style.left = '100px';
        input.style.width = '100px';
        input.style.height = '100px';
        input.style.zIndex = '999999';
        
        input.tabIndex = 0;
        input.focus();
        
        return "Focused file input";
    } catch(e) {
        return e.message;
    }
})();
"""
res = system_chrome.execute_javascript(w_idx, t_idx, js_focus_input)
print(f"JS result: {res}")

time.sleep(0.5)

# Trigger the file dialog with AppleScript by pressing Space or Return
trigger_script = '''
tell application "System Events"
    tell process "Google Chrome"
        set frontmost to true
        keystroke space
    end tell
end tell
'''
out, err = run_applescript(trigger_script)
print(f"Trigger space: {out} {err}")

time.sleep(1.5)

# Now check if Open dialog exists and upload!
abs_path = "/Users/linwang/src/github/xiluo/skills/blogger/articles/test_data/illustration.png"

upload_script = f'''
tell application "System Events"
    tell process "Google Chrome"
        set windowNames to name of every window
        if "Open" is in windowNames or "打开" is in windowNames then
            keystroke "g" using {{command down, shift down}}
            delay 1.0
            
            set the clipboard to "{abs_path}"
            keystroke "v" using {{command down}}
            delay 0.5
            
            keystroke return
            delay 1.0
            
            keystroke return
            return "Upload successful"
        else
            return "No Open dialog found"
        end if
    end tell
end tell
'''
out2, err2 = run_applescript(upload_script)
print(f"Upload result: {out2} {err2}")

# Clean up input style
js_cleanup = """
(function() {
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    if (fileInputs.length > 0) {
        fileInputs[0].style.display = 'none';
        fileInputs[0].style.position = '';
        fileInputs[0].style.top = '';
        fileInputs[0].style.left = '';
        fileInputs[0].style.zIndex = '';
        fileInputs[0].tabIndex = -1;
    }
})();
"""
system_chrome.execute_javascript(w_idx, t_idx, js_cleanup)
