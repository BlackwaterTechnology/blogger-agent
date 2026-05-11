#!/usr/bin/env bash
#
# Launch the regular Google Chrome with the default user-data-dir —
# i.e. your everyday browsing Chrome with all logins, cookies, tabs,
# bookmarks, and extensions exactly as they were.
#
# Pairs with launch-chrome-cdp.sh: that one runs an automation-only
# Chrome in a private user-data-dir for blogger to drive via CDP;
# this one starts your regular browsing Chrome. Both can coexist
# because macOS allows multiple Chrome instances as long as each
# has its own --user-data-dir.
#
# Why not just `open -a "Google Chrome"`: when any Chrome instance
# is already running (e.g. the CDP one), macOS LaunchServices
# forwards the `open` request to that existing instance and silently
# drops the --user-data-dir flag — you'd just bring the CDP Chrome
# to the front instead of starting a fresh default-profile instance.
# Spawning the binary directly bypasses LaunchServices.

set -euo pipefail

CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_USER_DATA="$HOME/Library/Application Support/Google/Chrome"

if [[ ! -x "$CHROME_BIN" ]]; then
    echo "Chrome binary not found at $CHROME_BIN" >&2
    exit 1
fi

# If a Chrome with the default user-data-dir is already running, do nothing.
# Bringing it to the foreground via `tell application` is ambiguous when
# two Chrome instances of the same bundle id coexist, so just inform.
if pgrep -f "user-data-dir=$DEFAULT_USER_DATA" >/dev/null 2>&1; then
    echo "Default Chrome is already running."
    echo "Use Mission Control (F3 / three-finger swipe) or right-click the Dock icon to switch to its window."
    exit 0
fi

"$CHROME_BIN" \
    --user-data-dir="$DEFAULT_USER_DATA" \
    "$@" >/dev/null 2>&1 &
chrome_pid=$!
disown
echo "Default Chrome launched (pid $chrome_pid). Sessions / tabs / extensions preserved."
echo "Tab restoration depends on your chrome://settings/onStartup preference."
echo "If tabs didn't come back: Cmd+Shift+T to reopen recently closed."
