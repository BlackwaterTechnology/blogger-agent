from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass




@dataclass
class ChromeDomController:
    app_name: str = "Google Chrome"
    script_timeout_seconds: float = 10.0

    def find_global_tab(self, url_prefixes: list[str]) -> tuple[int, int]:
        condition = self._build_url_prefix_condition(url_prefixes)
        script = f'''
tell application "{self.app_name}"
  repeat with w from 1 to count of windows
    set tabCount to count of tabs of window w
    repeat with t from 1 to tabCount
      set tabUrl to ""
      try
        set tabUrl to URL of tab t of window w
      end try
      if {condition} then
        set index of window w to 1
        set active tab index of window 1 to t
        activate
        return "1" & linefeed & (t as text)
      end if
    end repeat
  end repeat
  return ""
end tell
'''
        raw = self._run_osascript(script).strip()
        if not raw:
            raise RuntimeError(f"chrome global tab not found for prefixes: {url_prefixes!r}")
        w_text, _, t_text = raw.partition("\n")
        try:
            return int(w_text.strip()), int(t_text.strip())
        except ValueError as exc:
            raise RuntimeError(f"unexpected global tab return: {raw!r}") from exc

    def find_window_index_any(self, title_candidates: list[str]) -> int:
        return self._raise_and_resolve_window(title_candidates)[0]

    def find_window_name_any(self, title_candidates: list[str]) -> str:
        return self._raise_and_resolve_window(title_candidates)[1]

    def _raise_and_resolve_window(self, title_candidates: list[str]) -> tuple[int, str]:
        if not title_candidates:
            raise RuntimeError("chrome window marker list is empty")
        conditions = " or ".join(
            f'windowTitle contains "{self._escape_applescript(candidate)}"' for candidate in title_candidates
        )
        script = f'''
tell application "System Events"
  tell process "{self.app_name}"
    set matchedName to missing value
    repeat with windowIndex from 1 to count of windows
      set windowTitle to ""
      try
        set windowTitle to name of window windowIndex
      end try
      if {conditions} then
        set matchedName to windowTitle
        perform action "AXRaise" of window windowIndex
        set frontmost to true
        exit repeat
      end if
    end repeat
    if matchedName is missing value then
      return ""
    end if
  end tell
end tell

delay 0.1

tell application "{self.app_name}"
  return (index of front window as text) & linefeed & matchedName
end tell
'''
        raw = self._run_osascript(script).strip()
        if not raw:
            raise RuntimeError(f"chrome window not found for markers: {title_candidates!r}")
        window_index_text, _, window_name = raw.partition("\n")
        try:
            return int(window_index_text.strip()), window_name.strip()
        except ValueError as exc:
            raise RuntimeError(f"unexpected chrome window index value: {raw!r}") from exc

    def raise_window(self, window_index: int) -> str:
        script = f'''
tell application "System Events"
  tell process "{self.app_name}"
    set windowName to name of window {window_index}
    perform action "AXRaise" of window {window_index}
    set frontmost to true
    return windowName
  end tell
end tell
'''
        raw = self._run_osascript(script).strip()
        if not raw:
            raise RuntimeError(f"chrome window not found at index: {window_index}")
        return raw

    def activate_window(self, title_contains: str) -> None:
        self.activate_window_any([title_contains])

    def activate_window_any(self, title_candidates: list[str]) -> str:
        return self.find_window_name_any(title_candidates)

    def find_tab_index(self, window_index: int, *, url_prefixes: list[str] | None = None) -> int:
        script = f'''
tell application "{self.app_name}"
  repeat with tabIndex from 1 to count of tabs of window {window_index}
    set tabUrl to URL of tab tabIndex of window {window_index}
    if {self._build_url_prefix_condition(url_prefixes)} then
      return tabIndex
    end if
  end repeat
end tell
'''
        raw = self._run_osascript(script).strip()
        if not raw:
            raise RuntimeError(
                f"chrome tab not found in window {window_index} prefixes={url_prefixes!r}"
            )
        try:
            return int(raw)
        except ValueError as exc:
            raise RuntimeError(f"unexpected chrome tab index value: {raw!r}") from exc

    def find_tab_index_in_front_window(self, *, url_prefixes: list[str] | None = None) -> int:
        script = f'''
tell application "{self.app_name}"
  return index of front window
end tell
'''
        raw = self._run_osascript(script).strip()
        if not raw:
            raise RuntimeError("chrome front window not found")
        try:
            return self.find_tab_index(int(raw), url_prefixes=url_prefixes)
        except ValueError as exc:
            raise RuntimeError(f"unexpected chrome front window index value: {raw!r}") from exc

    def activate_tab(self, window_index: int, tab_index: int) -> None:
        script = f'''
tell application "{self.app_name}"
  set active tab index of window {window_index} to {tab_index}
end tell
'''
        self._run_osascript(script)

    def activate_tab_in_front_window(self, tab_index: int) -> None:
        script = f'''
tell application "{self.app_name}"
  set active tab index of front window to {tab_index}
  set index of front window to 1
  activate
end tell
'''
        self._run_osascript(script)

    def execute_javascript(
        self,
        window_index: int,
        tab_index: int,
        javascript: str,
        *,
        settle_seconds: float = 0.5,
    ) -> str:
        escaped_js = self._escape_applescript(javascript)
        script = f'''
tell application "{self.app_name}"
  set active tab index of window {window_index} to {tab_index}
  delay {settle_seconds}
  return execute tab {tab_index} of window {window_index} javascript "{escaped_js}"
end tell
'''
        try:
            return self._run_osascript(script)
        except RuntimeError as exc:
            if "Allow JavaScript from Apple Events" in str(exc):
                raise RuntimeError(
                    "AppleScript execution was blocked by macOS Chrome. "
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
        escaped_url = self._escape_applescript(url)
        script = f'''
tell application "{self.app_name}"
  set active tab index of window {window_index} to {tab_index}
  set URL of tab {tab_index} of window {window_index} to "{escaped_url}"
  delay {settle_seconds}
  return URL of tab {tab_index} of window {window_index}
end tell
'''
        return self._run_osascript(script).strip()

    def get_tab_url(self, window_index: int, tab_index: int) -> str:
        script = f'tell application "{self.app_name}" to return URL of tab {tab_index} of window {window_index}'
        return self._run_osascript(script).strip()
        
    def close_tab(self, window_index: int, tab_index: int) -> None:
        script = f'tell application "{self.app_name}" to close tab {tab_index} of window {window_index}'
        self._run_osascript(script)
        
    def get_cookie(self, name: str, domain: str) -> str:
        try:
            import rookiepy
            cookies = rookiepy.chrome([domain])
            for c in cookies:
                if c.get("name") == name:
                    return c.get("value", "")
        except Exception as exc:
            from loguru import logger
            logger.warning(f"rookiepy failed to extract cookie {name}: {exc}")
        return ""

    def resolve_window_and_tab(
        self,
        *,
        title_candidates: list[str],
        url_prefixes: list[str] | None = None,
    ) -> tuple[int, int]:
        try:
            window_index = self.find_window_index_any(title_candidates)
            tab_index = self.find_tab_index(window_index, url_prefixes=url_prefixes)
            return window_index, tab_index
        except RuntimeError as orig_exc:
            if url_prefixes:
                try:
                    return self.find_global_tab(url_prefixes)
                except RuntimeError:
                    pass
            
            if title_candidates:
                profile_name = title_candidates[0]
                target_url = url_prefixes[0] if url_prefixes else f"data:text/html;charset=utf-8,<title>{profile_name}</title>"
                import time
                from loguru import logger
                logger.info(f"auto-launching chrome profile: {profile_name}")
                try:
                    subprocess.run(
                        [
                            "open",
                            "-a",
                            self.app_name,
                            target_url
                        ],
                        check=True
                    )
                    time.sleep(6.0)
                    try:
                        if url_prefixes:
                            return self.find_global_tab(url_prefixes)
                        window_index = self.find_window_index_any(title_candidates)
                        return window_index, 1
                    except RuntimeError:
                        pass
                except Exception as e:
                    logger.warning(f"failed to auto-launch chrome profile: {e}")
                    
            raise orig_exc

    def execute_json(
        self,
        window_title_contains: str,
        *,
        url_prefixes: list[str],
        javascript: str,
        settle_seconds: float = 0.5,
    ) -> dict:
        window_index, tab_index = self.resolve_window_and_tab(
            title_candidates=[window_title_contains],
            url_prefixes=url_prefixes,
        )
        raw = self.execute_javascript(
            window_index,
            tab_index,
            javascript,
            settle_seconds=settle_seconds,
        ).strip()
        if not raw:
            raise RuntimeError("chrome javascript returned empty payload")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"failed to decode chrome javascript payload: {raw!r}") from exc

    def execute_json_in_front_tab(
        self,
        *,
        window_index: int,
        tab_index: int,
        javascript: str,
        settle_seconds: float = 0.5,
    ) -> dict:
        raw = self.execute_javascript(
            window_index,
            tab_index,
            javascript,
            settle_seconds=settle_seconds,
        ).strip()
        if not raw:
            raise RuntimeError("chrome javascript returned empty payload")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"failed to decode chrome javascript payload: {raw!r}") from exc

    def _run_osascript(self, script: str) -> str:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.script_timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise RuntimeError(f"failed to run osascript: {stderr}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("osascript timed out") from exc
        return result.stdout

    def _escape_applescript(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _build_url_prefix_condition(self, url_prefixes: list[str] | None) -> str:
        if not url_prefixes:
            return "true"
        return " or ".join(
            f'tabUrl contains "{self._escape_applescript(prefix)}"' for prefix in url_prefixes
        )


def email_to_profile_markers(email: str) -> list[str]:
    local_part = email.split("@", 1)[0].strip()
    if not local_part:
        return [email]
    segments = [segment for segment in local_part.split(".") if segment]
    pretty = " ".join(
        segment[:1].upper() + segment[1:] if segment else segment
        for segment in segments
    )
    candidates = [email, local_part]
    if pretty:
        candidates.append(pretty)
        candidates.append(f"Beiji ({pretty})")
    return list(dict.fromkeys(candidates))
