import json
import subprocess
import time
from dataclasses import dataclass

@dataclass
class JxaChromeController:
    app_name: str = "Google Chrome"
    script_timeout_seconds: float = 10.0
    target_pid: int = None
    prefer_default: bool = True

    def _check_and_fix_routing(self) -> None:
        """
        Detects if macOS Apple Events are incorrectly routed to the CDP Chrome instance
        instead of the default Chrome instance. If so, temporarily closes the CDP Chrome
        instance to force macOS to route events to the default Chrome instance, and registers
        an exit handler to restart the CDP Chrome.
        """
        import os
        import urllib.request
        import urllib.error
        import atexit
        from pathlib import Path
        from loguru import logger

        if not self.prefer_default:
            return

        # 1. Get page URLs from the CDP endpoint
        port = os.environ.get("BLOGGER_CDP_PORT", "9222")
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/json")
            with urllib.request.urlopen(req, timeout=1.0) as response:
                cdp_data = json.loads(response.read().decode())
            cdp_urls = {item.get("url") for item in cdp_data if "url" in item and item.get("type") == "page"}
        except Exception:
            cdp_urls = set()

        if not cdp_urls:
            return

        # 2. Get open URLs from the target targeted by JXA
        try:
            script = '''
            function run() {
                var urls = [];
                var chrome = Application("Google Chrome");
                for (var w = 0; w < chrome.windows.length; w++) {
                    var win = chrome.windows[w];
                    for (var t = 0; t < win.tabs.length; t++) {
                        urls.push(win.tabs[t].url());
                    }
                }
                return urls.join("\\n");
            }
            '''
            res = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True, text=True, check=True, timeout=5.0
            )
            jxa_urls = {u for u in res.stdout.strip().split("\n") if u}
        except Exception as e:
            logger.warning(f"Failed to query JXA URLs: {e}")
            jxa_urls = set()

        if not jxa_urls:
            return

        # 3. If JXA URLs are a subset of CDP URLs, JXA is routing to the CDP Chrome
        if jxa_urls.issubset(cdp_urls):
            logger.warning("macOS is routing Apple Events to the CDP Chrome instance instead of the default Chrome.")
            logger.info("Temporarily closing the CDP Chrome instance to fix routing...")
            
            user_data_dir = os.environ.get("BLOGGER_CDP_USER_DATA_DIR", os.path.expanduser("~/.blogger-chrome-cdp"))
            try:
                # Terminate the CDP Chrome process using pkill
                subprocess.run(["pkill", "-f", f"user-data-dir={user_data_dir}"], check=False)
                # Wait up to 3 seconds for it to exit
                for _ in range(30):
                    time.sleep(0.1)
                    # Check if port is closed
                    try:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=0.1):
                            pass
                    except Exception:
                        break
                logger.info("CDP Chrome instance closed. Apple Events will now route to the default Chrome.")
                
                # Register exit handler to restart CDP Chrome
                def restart_cdp():
                    logger.info("Restarting CDP Chrome instance...")
                    script_path = Path(__file__).parent.parent.parent.parent / "tools" / "launch-chrome-cdp.sh"
                    if script_path.exists():
                        subprocess.Popen(
                            [str(script_path)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        logger.info("CDP Chrome restarted in background.")
                
                atexit.register(restart_cdp)
            except Exception as e:
                logger.warning(f"Failed to close or schedule restart for CDP Chrome: {e}")

    def _get_chrome_pids(self, prefer_default: bool = True) -> list[int]:
        """
        Retrieve running Chrome process IDs via `ps` command-line tools.
        Prioritizes default profile vs. CDP profiles.
        """
        try:
            res = subprocess.run(
                ["ps", "-ax", "-o", "pid,command"],
                capture_output=True, text=True, check=True
            )
            lines = res.stdout.strip().split("\n")
        except Exception as e:
            from loguru import logger
            logger.warning(f"Failed to list Chrome processes via ps: {e}")
            return []

        default_pids = []
        cdp_pids = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            pid_str, cmd = parts
            
            # Match only the main Google Chrome processes, not helpers, renderers or crashpads
            if "Google Chrome" in cmd and "Google Chrome Helper" not in cmd and "Contents/MacOS/Google Chrome" in cmd:
                try:
                    pid = int(pid_str)
                except ValueError:
                    continue
                
                # If command line contains remote-debugging-port, it's a CDP instance
                is_cdp = "--remote-debugging-port" in cmd
                if is_cdp:
                    cdp_pids.append(pid)
                else:
                    default_pids.append(pid)
                    
        # Remove duplicates while maintaining order
        default_pids = list(dict.fromkeys(default_pids))
        cdp_pids = list(dict.fromkeys(cdp_pids))
        
        if prefer_default:
            return default_pids + cdp_pids
        else:
            return cdp_pids + default_pids

    def find_global_tab(self, url_prefixes: list[str]) -> tuple[int, int]:
        self._check_and_fix_routing()
        pids = self._get_chrome_pids(prefer_default=self.prefer_default)
        if not pids:
            raise RuntimeError("No Google Chrome processes running.")

        prefixes_json = json.dumps(url_prefixes)
        pids_json = json.dumps(pids)
        script = f'''
function run() {{
    var prefixes = {prefixes_json};
    var pids = {pids_json};
    
    for (var i=0; i<pids.length; i++) {{
        var pid = pids[i];
        try {{
            var chrome = Application(pid);
            if (!chrome || !chrome.windows) continue;
            var winCount = chrome.windows.length;
            for (var w = 0; w < winCount; w++) {{
                try {{
                    var win = chrome.windows[w];
                    if (!win || !win.tabs) continue;
                    var tabCount = win.tabs.length;
                    for (var t = 0; t < tabCount; t++) {{
                        try {{
                            var tab = win.tabs[t];
                            if (!tab) continue;
                            var url = tab.url();
                            if (!url) continue;

                            for (var p = 0; p < prefixes.length; p++) {{
                                if (url.indexOf(prefixes[p]) !== -1) {{
                                    var winId = win.id();
                                    var tabId = tab.id();
                                    win.index = 1;
                                    win.activeTabIndex = t + 1;
                                    chrome.activate();
                                    return pid + "\\n" + winId + "\\n" + tabId;
                                }}
                            }}
                        }} catch(e) {{ continue; }}
                    }}
                }} catch(e) {{ continue; }}
            }}
        }} catch(e) {{ continue; }}
    }}
    return "";
}}
'''
        raw = self._run_jxa(script).strip()
        if not raw:
            raise RuntimeError(f"chrome global tab not found for prefixes: {url_prefixes!r}")
        
        parts = raw.split("\n")
        if len(parts) == 3:
            self.target_pid = int(parts[0].strip())
            return int(parts[1].strip()), int(parts[2].strip())
        raise RuntimeError(f"unexpected global tab return: {raw!r}")

    def create_tab(self, url: str) -> tuple[int, int]:
        if self.target_pid is None:
            pids = self._get_chrome_pids(prefer_default=self.prefer_default)
            if not pids:
                raise RuntimeError("No Google Chrome processes running.")
            self.target_pid = pids[0]
            
        escaped_url = json.dumps(url)
        script = f'''
function run() {{
    var chrome = Application({self.target_pid});
    if (chrome.windows.length === 0) {{
        chrome.windows.push(chrome.Window());
    }}
    var win = chrome.windows[0];
    var tab = chrome.Tab({{url: {escaped_url}}});
    win.tabs.push(tab);
    var winId = win.id();
    var tabId = tab.id();
    return winId + "\\n" + tabId;
}}
'''
        raw = self._run_jxa(script).strip()
        parts = raw.split("\n")
        return int(parts[0].strip()), int(parts[1].strip())

    def close_tab(self, window_id: int, tab_id: int) -> None:
        script = f'''
function run() {{
    var chrome = {self._get_app_ref()};
    var win = chrome.windows.byId({window_id});
    var tab = win.tabs.byId({tab_id});
    tab.close();
}}
'''
        self._run_jxa(script)

    def _get_app_ref(self) -> str:
        if self.target_pid:
            return f'Application({self.target_pid})'
        return f'Application("{self.app_name}")'

    def execute_javascript(
        self,
        window_id: int,
        tab_id: int,
        javascript: str,
        *,
        settle_seconds: float = 0.5,
    ) -> str:
        escaped_js = json.dumps(javascript)
        script = f'''
function run() {{
    var chrome = {self._get_app_ref()};
    var win = chrome.windows.byId({window_id});
    var tab = win.tabs.byId({tab_id});
    
    for (var i = 0; i < win.tabs.length; i++) {{
        if (win.tabs[i].id() === {tab_id}) {{
            win.activeTabIndex = i + 1;
            break;
        }}
    }}
    
    delay({settle_seconds});
    return tab.execute({{javascript: {escaped_js}}});
}}
'''
        try:
            return self._run_jxa(script)
        except RuntimeError as exc:
            if "Allow JavaScript from Apple Events" in str(exc):
                raise RuntimeError(
                    "JavaScript execution was blocked by macOS Chrome. "
                    "You must manually tick 'View -> Developer -> Allow JavaScript from Apple Events' "
                    "in the specific Chrome profile window."
                ) from exc
            raise

    def set_tab_url(
        self,
        window_id: int,
        tab_id: int,
        url: str,
        *,
        settle_seconds: float = 1.0,
    ) -> str:
        escaped_url = json.dumps(url)
        script = f'''
function run() {{
    var chrome = {self._get_app_ref()};
    var win = chrome.windows.byId({window_id});
    var tab = win.tabs.byId({tab_id});
    
    for (var i = 0; i < win.tabs.length; i++) {{
        if (win.tabs[i].id() === {tab_id}) {{
            win.activeTabIndex = i + 1;
            break;
        }}
    }}
    
    tab.url = {escaped_url};
    delay({settle_seconds});
    return tab.url();
}}
'''
        return self._run_jxa(script).strip()

    def get_tab_url(self, window_id: int, tab_id: int) -> str:
        script = f'''
function run() {{
    var chrome = {self._get_app_ref()};
    return chrome.windows.byId({window_id}).tabs.byId({tab_id}).url();
}}
'''
        return self._run_jxa(script).strip()

    def run_in_chrome_process(self, inner_body: str, *, check: bool = True) -> subprocess.CompletedProcess:
        if self.target_pid is not None:
            script = (
                'tell application "System Events"\n'
                f'    set theProcess to (first process whose unix id is {self.target_pid})\n'
                '    tell theProcess\n'
                '        set frontmost to true\n'
                '        delay 0.2\n'
                f'{inner_body}\n'
                '    end tell\n'
                'end tell\n'
            )
        else:
            script = (
                'tell application "System Events"\n'
                f'    tell process "{self.app_name}"\n'
                '        set frontmost to true\n'
                '        delay 0.2\n'
                f'{inner_body}\n'
                '    end tell\n'
                'end tell\n'
            )
        return subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, check=check,
        )

    def _run_jxa(self, script: str) -> str:
        try:
            result = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.script_timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise RuntimeError(f"failed to run jxa script: {stderr}\nOutput: {exc.stdout}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("jxa script timed out") from exc
        return result.stdout
