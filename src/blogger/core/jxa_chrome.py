import json
import subprocess
from dataclasses import dataclass

@dataclass
class JxaChromeController:
    app_name: str = "Google Chrome"
    script_timeout_seconds: float = 10.0
    target_pid: int = None

    def find_global_tab(self, url_prefixes: list[str]) -> tuple[int, int]:
        prefixes_json = json.dumps(url_prefixes)
        script = f'''
function run() {{
    var appName = "{self.app_name}";
    var se = Application("System Events");
    var procs = se.processes.whose({{name: appName}});
    var pids = [];
    for (var i=0; i<procs.length; i++) {{
        pids.push(procs[i].unixId());
    }}
    
    var prefixes = {prefixes_json};
    
    for (var i=0; i<pids.length; i++) {{
        var pid = pids[i];
        try {{
            var chrome = Application(pid);
            var winCount = chrome.windows.length;
            for (var w = 0; w < winCount; w++) {{
                var win = chrome.windows[w];
                var tabCount = win.tabs.length;
                for (var t = 0; t < tabCount; t++) {{
                    var tab = win.tabs[t];
                    var url = tab.url();
                    if (!url) continue;

                    for (var p = 0; p < prefixes.length; p++) {{
                        if (url.startsWith(prefixes[p])) {{
                            var winId = win.id();
                            var tabId = tab.id();
                            win.index = 1;
                            win.activeTabIndex = t + 1;
                            chrome.activate();
                            return pid + "\\n" + winId + "\\n" + tabId;
                        }}
                    }}
                }}
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
