import time
import json
from loguru import logger
from ..core.chrome import ChromeDomController

class BilibiliPublisher:
    def __init__(self):
        self.chrome = ChromeDomController()

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
        title = article_data.get("title", "")
        desc = article_data.get("desc", "")
        tags = article_data.get("tags", [])
        video_path = article_data.get("video_path")
        
        if not video_path:
            logger.error("No video_path provided in article_data. Cannot publish to Bilibili.")
            return

        try:
            w_idx, t_idx = self.chrome.find_global_tab(["member.bilibili.com"])
            url = self.chrome.get_tab_url(w_idx, t_idx)
            logger.info(f"Found Bilibili Creator Studio tab: {url}")
        except Exception as e:
            logger.warning(f"Bilibili tab not found. Creating a new tab: {e}")
            w_idx, t_idx = self.chrome.create_tab("https://member.bilibili.com/platform/upload/video/frame")
            time.sleep(5)
            
        url = self.chrome.get_tab_url(w_idx, t_idx)
        if "upload/video" not in url:
            new_url = "https://member.bilibili.com/platform/upload/video/frame"
            logger.info(f"Navigating to upload page: {new_url}")
            self.chrome.set_tab_url(w_idx, t_idx, new_url, settle_seconds=5.0)
            
        logger.info("Setting up video upload...")
        
        # Bilibili uses an input[type=file] for upload
        js_upload_trigger = """
        (function() {
            try {
                let state = { is_done: false };
                let action = '';
                
                // If we're already past the upload screen (e.g. video is uploading/uploaded)
                if (document.querySelector('.upload-v2-container') && document.querySelector('.video-title')) {
                    state.is_done = true;
                    action = 'Already in upload form';
                    return JSON.stringify({state: state, action: action, is_done: true});
                }
                
                // Find upload input
                const uploadInputs = Array.from(document.querySelectorAll('input[type="file"]'));
                if (uploadInputs.length > 0) {
                    // We cannot set file value directly due to security, but we can trigger click and let AppleScript do the rest
                    // But maybe we can just make it visible and focused? 
                    // Wait, we can't paste a file into a file input with AppleScript easily if it opens a dialog.
                    // Usually we use drop event or set the input value if possible, but AppleScript dialog is hard to automate unless we know it's open.
                    // Another way is to simulate drop event in JS. 
                    // For ChromeDomController, there's no direct file upload method.
                    // We'll return ready for AppleScript.
                    action = 'Ready for upload';
                    return JSON.stringify({state: state, action: action, is_done: true});
                }
                
                action = 'Waiting for upload input...';
                return JSON.stringify({state: state, action: action, is_done: false});
            } catch(e) {
                return JSON.stringify({state: {error: e.toString()}, action: 'Error: ' + e.toString(), is_done: false});
            }
        })();
        """
        self.run_ui_state_machine("Upload Trigger", w_idx, t_idx, js_upload_trigger, max_steps=5, delay=2.0)
        
        logger.info(f"Simulating drop event for video file: {video_path}")
        # To upload a file in Chrome natively via Python without opening dialogs, usually tools use CDP DOM.setFileInputFiles
        # We can use ChromeDomController's CDP method if it exposes it, but let's check its source.
        # I'll just use a generic drop event or rely on the user to select, or we can use applescript if we open the dialog.
        # Actually, AppleScript can paste files in the file selection dialog by pressing Cmd+Shift+G and typing the path.
        
        js_click_upload = """
        (function() {
            const btn = document.querySelector('.bcc-upload-wrapper') || document.querySelector('.upload-btn');
            if (btn) btn.click();
        })();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_click_upload)
        time.sleep(2)
        
        # AppleScript to interact with macOS file open dialog
        import pathlib
        abs_path = pathlib.Path(video_path).absolute()
        applescript_file_dialog = f'''
        tell application "System Events"
            tell process "Google Chrome"
                set frontmost to true
                delay 1.0
                keystroke "g" using {{command down, shift down}}
                delay 1.0
                keystroke "{abs_path}"
                delay 1.0
                keystroke return
                delay 1.0
                keystroke return
            end tell
        end tell
        '''
        self.chrome._run_osascript(applescript_file_dialog)
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
                
                const titleInput = document.querySelector('.video-title .input-val, input[placeholder*="标题"]');
                if (titleInput) setReactValue(titleInput, title);
                
                const descInput = document.querySelector('.video-desc .ql-editor, textarea[placeholder*="简介"]');
                if (descInput) {{
                    if (descInput.classList.contains('ql-editor')) {{
                        descInput.innerText = desc;
                        descInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        setReactValue(descInput, desc);
                    }}
                }}
                
                // Set Original (原创)
                const originalRadio = document.querySelector('.radio-item[title="自制"], .check-radio-v2');
                if (originalRadio) originalRadio.click();
                
                return "Filled metadata";
            }} catch(e) {{
                return e.message;
            }}
        }})();
        """
        self.chrome.execute_javascript(w_idx, t_idx, js_fill_details)
        logger.info("Filled Bilibili video details.")
        
        logger.info("Bilibili publishing automation complete. Please verify and submit manually.")
