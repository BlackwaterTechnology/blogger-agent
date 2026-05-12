"""CDP-based replacement for JxaChromeController.

This provides the same four-method surface the juejin/csdn publishers use —
find_global_tab / get_tab_url / set_tab_url / execute_javascript — but
backed by Chrome DevTools Protocol over WebSocket instead of AppleScript /
JXA. It removes every dependency on:

- macOS Accessibility permission (osascript-via-System-Events)
- The "frontmost Chrome" ambiguity when two Chrome instances run side by side
- AppleScript-injected JS lacking user-activation transient (file picker)

Prerequisites:
- Chrome launched with `--remote-debugging-port=9222`. Use
  `tools/launch-chrome-cdp.sh` — it picks a dedicated user-data-dir
  (`~/.blogger-chrome-cdp`) so your day-to-day Chrome can keep running
  independently.
- websocket-client Python package (already a transitive dep).

Two extras on top of the JXA-compatible surface:
- `set_file_input(selector, file_path)` — DOM.setFileInputFiles for
  cover uploads, replacing the physical-click + Cmd-Shift-G dance.
- `activate()` — raises the CDP Chrome process to the foreground via its
  pid, so legacy osascript keystroke calls (pbcopy + Cmd+V) still hit
  the right instance.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import websocket  # websocket-client


class CdpChromeUnavailable(RuntimeError):
    """The Chrome remote-debug port is unreachable. The user almost
    certainly forgot to run tools/launch-chrome-cdp.sh."""


def _default_port() -> int:
    try:
        return int(os.environ.get("BLOGGER_CDP_PORT", "9222"))
    except ValueError:
        return 9222


@dataclass
class CdpChromeController:
    """Tab driver that speaks CDP over the local Chrome debugger port.

    `window_id` is kept in the API only for compatibility with the
    JXA controller's tuple shape — it's always 0 here. The "tab"
    identifier is Chrome's targetId (a UUID string), passed through
    opaquely.
    """

    port: int = field(default_factory=_default_port)
    timeout: float = 5.0
    # Cache of long-lived per-target WebSocket sessions. We need these for
    # Page.addScriptToEvaluateOnNewDocument: that command's effect lives
    # only as long as the session does, so if every CDP call opens and
    # closes its own WebSocket the stealth script never survives to the
    # next page navigation. Keyed by target_id; values are open WebSocket
    # connections, each preconfigured with stealth.
    _sessions: dict = field(default_factory=dict)
    _msg_id: int = 0

    # ---- HTTP /json -----------------------------------------------------

    def _list_targets(self) -> list[dict[str, Any]]:
        url = f"http://127.0.0.1:{self.port}/json"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            raise CdpChromeUnavailable(
                f"Cannot reach Chrome remote-debugger on port {self.port}: {exc}. "
                f"Launch Chrome with tools/launch-chrome-cdp.sh (or set "
                f"BLOGGER_CDP_PORT)."
            ) from exc

    # ---- WebSocket calls ------------------------------------------------

    def _get_session(self, target_id: str):
        """Return a persistent WebSocket session for this target, opening
        one on first request and installing the stealth on-new-document
        script before any other call. Subsequent calls reuse the session
        so the stealth install survives across page navigations."""
        ws = self._sessions.get(target_id)
        if ws is not None:
            return ws

        targets = self._list_targets()
        tgt = next((t for t in targets if t.get("id") == target_id), None)
        if not tgt:
            raise RuntimeError(f"CDP target {target_id!r} not found")
        ws_url = tgt.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError(f"CDP target {target_id!r} has no webSocketDebuggerUrl")
        ws = websocket.create_connection(ws_url, timeout=self.timeout)
        self._sessions[target_id] = ws

        # Install stealth right now, in this session, so any future
        # navigation in this tab gets the script before page JS runs.
        try:
            self._raw_call(ws, "Page.enable")
            self._raw_call(ws, "Page.addScriptToEvaluateOnNewDocument",
                           {"source": self._STEALTH_SCRIPT})
        except Exception:
            # best-effort; controller still works without stealth
            pass
        return ws

    def _raw_call(self, ws, method: str, params: dict | None = None) -> dict:
        """Send one command on the given WebSocket and wait for its reply.
        Drains unrelated async events while waiting."""
        self._msg_id += 1
        my_id = self._msg_id
        ws.send(json.dumps({"id": my_id, "method": method, "params": params or {}}))
        while True:
            raw = ws.recv()
            msg = json.loads(raw)
            if msg.get("id") != my_id:
                continue
            if "error" in msg:
                raise RuntimeError(f"CDP {method} failed: {msg['error']}")
            return msg.get("result", {})

    def _call_on(self, target_id: str, method: str, params: dict | None = None) -> dict:
        """Public-ish entry point: get (or open) the persistent session for
        target_id and run a single command on it."""
        ws = self._get_session(target_id)
        try:
            return self._raw_call(ws, method, params)
        except (websocket.WebSocketConnectionClosedException, ConnectionError, OSError):
            # Session died — drop from cache and retry once with a fresh one.
            try:
                ws.close()
            except Exception:
                pass
            self._sessions.pop(target_id, None)
            ws = self._get_session(target_id)
            return self._raw_call(ws, method, params)

    # ---- Stealth: hide CDP fingerprint from anti-bot scripts ---------
    #
    # Chrome's `--remote-debugging-port` flag triggers the AutomationControlled
    # feature, which removes `window.chrome.runtime` and (in some versions)
    # sets `navigator.webdriver = true`. Some sites — mp.weixin.qq.com is one
    # — detect these and show a "browser plugin has security issues" dialog
    # that blocks the editor.
    #
    # The launch script already passes --disable-blink-features=AutomationControlled
    # and --exclude-switches=enable-automation; on top of that we install
    # Page.addScriptToEvaluateOnNewDocument so that every future navigation
    # in this tab gets a chrome.runtime stub and `navigator.webdriver=undefined`
    # injected before any page script runs.

    _STEALTH_SCRIPT = r"""
    (function(){
      try { window.__blogger_stealth_loaded = Date.now(); } catch(e) {}
      try {
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      } catch(e) {}
      try {
        if (typeof window.chrome === 'object' && !window.chrome.runtime) {
          window.chrome.runtime = {
            id: undefined,
            OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
            OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
            PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
            PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
            RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
            connect: function(){ return { onMessage: { addListener: function(){}, removeListener: function(){} }, onDisconnect: { addListener: function(){}, removeListener: function(){} }, postMessage: function(){}, disconnect: function(){} }; },
            sendMessage: function(){},
            getURL: function(p){ return p; },
            getManifest: function(){ return {}; },
          };
        }
      } catch(e) {}
      try {
        const desired = ['zh-CN', 'zh', 'en-US', 'en'];
        if (!navigator.languages || navigator.languages[0] !== 'zh-CN') {
          Object.defineProperty(navigator, 'languages', { get: () => desired });
          Object.defineProperty(navigator, 'language', { get: () => 'zh-CN' });
        }
      } catch(e) {}
    })();
    """

    def _install_stealth(self, target_id: str) -> None:
        """Install the stealth script on a page target so that every future
        navigation has chrome.runtime / navigator.webdriver back in place.

        Has no effect on already-loaded pages — for those, reload the tab
        after the controller has run once.
        """
        try:
            self._call_on(
                target_id,
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": self._STEALTH_SCRIPT},
            )
        except Exception:
            # Best-effort; do not block the publisher if the install fails.
            pass

    # ---- Public API: matches JxaChromeController.find_global_tab ----

    def find_global_tab(self, url_prefixes: list[str]) -> tuple[int, str]:
        """Return (0, targetId) for the first page-type target whose URL
        starts with one of the given prefixes. Raises
        CdpChromeUnavailable if Chrome isn't running with CDP enabled
        — callers can catch that to print a clear error."""
        targets = self._list_targets()
        for t in targets:
            if t.get("type") != "page":
                continue
            url = t.get("url", "")
            for prefix in url_prefixes:
                if url.startswith(prefix):
                    self._install_stealth(t["id"])
                    try:
                        self._call_on(t["id"], "Page.bringToFront")
                    except Exception:
                        pass
                    return (0, t["id"])
        raise RuntimeError(
            f"No CDP page-tab matched prefixes {url_prefixes!r}. "
            f"Saw: {[t.get('url','') for t in targets if t.get('type')=='page']}"
        )

    def get_tab_url(self, window_id: int, tab_id: str) -> str:
        for t in self._list_targets():
            if t.get("id") == tab_id:
                return t.get("url", "")
        return ""

    def set_tab_url(
        self,
        window_id: int,
        tab_id: str,
        url: str,
        *,
        settle_seconds: float = 1.0,
    ) -> str:
        try:
            self._call_on(tab_id, "Page.bringToFront")
        except Exception:
            pass
        self._call_on(tab_id, "Page.navigate", {"url": url})
        if settle_seconds > 0:
            time.sleep(settle_seconds)
        return self.get_tab_url(window_id, tab_id)

    def execute_javascript(
        self,
        window_id: int,
        tab_id: str,
        javascript: str,
        *,
        settle_seconds: float = 0.5,
    ) -> str:
        """Evaluate JS in the page and return the result as a string.

        Matches JxaChromeController.execute_javascript semantics — the
        publisher code stores the return value and JSON.parses it, so we
        coerce here the same way: primitives → str, objects → JSON.
        """
        try:
            self._call_on(tab_id, "Page.bringToFront")
        except Exception:
            pass
        res = self._call_on(
            tab_id,
            "Runtime.evaluate",
            {
                "expression": javascript,
                "returnByValue": True,
                "awaitPromise": True,
                "userGesture": True,  # makes file-picker friendly inputs work
            },
        )
        if res.get("exceptionDetails"):
            details = res["exceptionDetails"]
            msg = details.get("exception", {}).get("description") or details.get("text", "")
            raise RuntimeError(f"CDP Runtime.evaluate JS exception: {msg}")
        if settle_seconds > 0:
            time.sleep(settle_seconds)
        value = res.get("result", {}).get("value")
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    # ---- CDP-only extensions -------------------------------------------

    def set_file_input(self, tab_id: str, selector: str, file_path: Path) -> None:
        """Inject `file_path` into the <input type="file"> matched by
        `selector`. Fires the same change event a real user click would,
        so the page's upload logic runs unchanged."""
        file_path = Path(file_path).expanduser().resolve()
        if not file_path.exists():
            raise RuntimeError(f"file not found: {file_path}")

        # Open one persistent session for the three calls we need.
        targets = self._list_targets()
        tgt = next((t for t in targets if t.get("id") == tab_id), None)
        if not tgt:
            raise RuntimeError(f"CDP target {tab_id!r} not found")
        ws = websocket.create_connection(tgt["webSocketDebuggerUrl"], timeout=self.timeout)
        msg_id = 0

        def call(method: str, params: dict | None = None) -> dict:
            nonlocal msg_id
            msg_id += 1
            ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
            while True:
                m = json.loads(ws.recv())
                if m.get("id") != msg_id:
                    continue
                if "error" in m:
                    raise RuntimeError(f"CDP {method} failed: {m['error']}")
                return m.get("result", {})

        try:
            call("DOM.enable")
            doc = call("DOM.getDocument", {"depth": 0})
            root_id = doc["root"]["nodeId"]
            match = call("DOM.querySelector", {"nodeId": root_id, "selector": selector})
            node_id = match.get("nodeId") or 0
            if not node_id:
                raise RuntimeError(f"selector {selector!r} matched no element on {tgt.get('url')!r}")
            call("DOM.setFileInputFiles", {"nodeId": node_id, "files": [str(file_path)]})
        finally:
            try:
                ws.close()
            except Exception:
                pass

    # ---- Side helpers for the legacy keystroke paths -------------------

    def _chrome_pid(self) -> int | None:
        """Find the pid of the Chrome process listening on our CDP port.
        Used by activate() to disambiguate when two Chrome instances are
        running side by side."""
        try:
            out = subprocess.check_output(
                ["lsof", "-nP", f"-iTCP:{self.port}", "-sTCP:LISTEN", "-t"],
                text=True,
                timeout=2,
            ).strip()
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    return int(line)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def activate(self) -> None:
        """Raise the CDP Chrome process to the foreground via its pid.
        Must be called before any legacy `osascript ... keystroke` so the
        keystrokes land in this Chrome instance rather than the user's
        regular Chrome (or any other app)."""
        pid = self._chrome_pid()
        if pid is None:
            # Fall back to activating by name; better than nothing.
            subprocess.run(
                ["osascript", "-e", 'tell application "Google Chrome" to activate'],
                capture_output=True, text=True, check=False,
            )
            return

        # Use native macOS AppKit API via JXA to explicitly activate the specific PID.
        # This completely bypasses the LaunchServices/WindowServer bug where AppleScript
        # "System Events" misroutes activation to the default Chrome instance.
        jxa_script = f"""
        ObjC.import('AppKit');
        var app = $.NSRunningApplication.runningApplicationWithProcessIdentifier({pid});
        if (app) {{
            app.activateWithOptions($.NSApplicationActivateIgnoringOtherApps);
        }}
        """
        subprocess.run(["osascript", "-l", "JavaScript", "-e", jxa_script], check=False)
        time.sleep(0.2)

    def run_in_chrome_process(self, inner_body: str, *, check: bool = True) -> subprocess.CompletedProcess:
        """Wrap `inner_body` in a `tell` block targeting the *CDP* Chrome
        process via its pid, then run it through osascript.

        This replaces the old `tell process "Google Chrome"` pattern, which
        is ambiguous when two Chrome instances are running (your day-to-day
        Chrome + the dedicated CDP Chrome) — System Events resolves the
        name to whichever instance it picks first, often the wrong one.

        `inner_body` should contain only the keystroke / key code / delay
        lines that belong inside `tell process ... end tell`. Example:

            self.chrome.run_in_chrome_process('''
                keystroke "v" using {command down}
                delay 0.5
            ''')

        Falls back to name-based addressing if the pid lookup fails,
        which is no worse than the legacy behavior."""
        pid = self._chrome_pid()
        if pid is not None:
            self.activate()
            script = (
                'tell application "System Events"\n'
                f'    set theProcess to (first process whose unix id is {pid})\n'
                '    tell theProcess\n'
                f'{inner_body}\n'
                '    end tell\n'
                'end tell\n'
            )
        else:
            script = (
                'tell application "System Events"\n'
                '    tell process "Google Chrome"\n'
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
