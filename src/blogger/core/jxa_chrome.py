import json
import subprocess
from dataclasses import dataclass

@dataclass
class JxaChromeController:
    app_name: str = "Google Chrome"
    script_timeout_seconds: float = 10.0

    def find_global_tab(self, url_prefixes: list[str]) -> tuple[int, int]:
        prefixes_json = json.dumps(url_prefixes)
        script = f"""
function run() {{
    var chrome = Application("{self.app_name}");
    var prefixes = {prefixes_json};
    
    for (var w = 0; w < chrome.windows.length; w++) {{
        var win = chrome.windows[w];
        for (var t = 0; t < win.tabs.length; t++) {{
            var tab = win.tabs[t];
            var url = "";
            try {{ url = tab.url(); }} catch(e) {{}}
            if (!url) continue;
            
            for (var p = 0; p < prefixes.length; p++) {{
                if (url.startsWith(prefixes[p])) {{
                    win.index = 1;
                    win.activeTabIndex = t + 1; // activeTabIndex is 1-indexed in JXA Chrome dictionary
                    chrome.activate();
                    return w + "\\n" + t;
                }}
            }}
        }}
    }}
    return "";
}}
"""
        raw = self._run_jxa(script).strip()
        if not raw:
            raise RuntimeError(f"chrome global tab not found for prefixes: {url_prefixes!r}")
        
        w_text, _, t_text = raw.partition("\n")
        try:
            return int(w_text.strip()), int(t_text.strip())
        except ValueError as exc:
            raise RuntimeError(f"unexpected global tab return: {raw!r}") from exc

    def execute_javascript(
        self,
        window_index: int,
        tab_index: int,
        javascript: str,
        *,
        settle_seconds: float = 0.5,
    ) -> str:
        escaped_js = json.dumps(javascript)
        script = f"""
function run() {{
    var chrome = Application("{self.app_name}");
    var win = chrome.windows[{window_index}];
    var tab = win.tabs[{tab_index}];
    win.activeTabIndex = {tab_index} + 1;
    delay({settle_seconds});
    return tab.execute({{javascript: {escaped_js}}});
}}
"""
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
        window_index: int,
        tab_index: int,
        url: str,
        *,
        settle_seconds: float = 1.0,
    ) -> str:
        escaped_url = json.dumps(url)
        script = f"""
function run() {{
    var chrome = Application("{self.app_name}");
    var win = chrome.windows[{window_index}];
    var tab = win.tabs[{tab_index}];
    win.activeTabIndex = {tab_index} + 1;
    tab.url = {escaped_url};
    delay({settle_seconds});
    return tab.url();
}}
"""
        return self._run_jxa(script).strip()

    def get_tab_url(self, window_index: int, tab_index: int) -> str:
        script = f"""
function run() {{
    var chrome = Application("{self.app_name}");
    return chrome.windows[{window_index}].tabs[{tab_index}].url();
}}
"""
        return self._run_jxa(script).strip()

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
            raise RuntimeError(f"failed to run jxa script: {stderr}\\nOutput: {exc.stdout}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("jxa script timed out") from exc
        return result.stdout
