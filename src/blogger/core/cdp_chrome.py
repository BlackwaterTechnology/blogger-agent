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

    def _call_on(self, target_id: str, method: str, params: dict | None = None) -> dict:
        """Open a per-target WebSocket, send one command, close."""
        targets = self._list_targets()
        tgt = next((t for t in targets if t.get("id") == target_id), None)
        if not tgt:
            raise RuntimeError(f"CDP target {target_id!r} not found")
        ws_url = tgt.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError(f"CDP target {target_id!r} has no webSocketDebuggerUrl")
        ws = websocket.create_connection(ws_url, timeout=self.timeout)
        try:
            ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
            while True:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("id") != 1:
                    continue  # Drain async event before our reply.
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} failed: {msg['error']}")
                return msg.get("result", {})
        finally:
            try:
                ws.close()
            except Exception:
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
        script = (
            'tell application "System Events"\n'
            f'    set procs to (every process whose unix id is {pid})\n'
            "    if (count of procs) > 0 then\n"
            "        set frontmost of (item 1 of procs) to true\n"
            "    end if\n"
            "end tell"
        )
        subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)

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
            script = (
                'tell application "System Events"\n'
                f'    set theProcess to (first process whose unix id is {pid})\n'
                '    set frontmost of theProcess to true\n'
                '    delay 0.2\n'
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
