#!/usr/bin/env bash
#
# Launch a dedicated Google Chrome instance with the Chrome DevTools
# Protocol remote-debug port enabled, so blogger can drive cover-image
# uploads via DOM.setFileInputFiles instead of the fragile AppleScript
# keystroke chain.
#
# Why a dedicated user-data-dir (not your default Chrome):
#   1. Your default profile is flagged "enterprise_profile_guid" because
#      one of your signed-in Google accounts is managed by a Workspace
#      domain. Chrome silently disables --remote-debugging-port for
#      enterprise profiles even when there's no explicit policy banning
#      it. Tested: same Chrome binary, same flag, isolated user-data-dir
#      binds the port; default user-data-dir does not.
#   2. Using a dedicated user-data-dir means your day-to-day Chrome and
#      this automation Chrome are independent — you can run both at the
#      same time, switch between them by Cmd+Tab, and never have to
#      quit one to launch the other.
#
# First run: this Chrome instance starts with empty cookies, so you'll
# need to sign in once to juejin/csdn/wechat-mp/etc. The dedicated dir
# persists, so subsequent runs reuse those logins.

set -euo pipefail

CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT="${BLOGGER_CDP_PORT:-9222}"
USER_DATA_DIR="${BLOGGER_CDP_USER_DATA_DIR:-$HOME/.blogger-chrome-cdp}"

if [[ ! -x "$CHROME_BIN" ]]; then
    echo "Chrome binary not found at $CHROME_BIN" >&2
    exit 1
fi

# Two independent Chrome instances with different user-data-dirs can coexist,
# but only one can use this specific dir at a time. Check for a running
# Chrome that already owns this dir.
if pgrep -f "user-data-dir=$USER_DATA_DIR" >/dev/null 2>&1; then
    echo "A Chrome instance is already running with user-data-dir=$USER_DATA_DIR."
    if curl -s -m 1 -o /dev/null -w "%{http_code}" "http://localhost:$PORT/json/version" | grep -q "^200$"; then
        echo "CDP endpoint http://localhost:$PORT is responding — nothing to do."
        exit 0
    fi
    echo "Existing instance does NOT have CDP on port $PORT." >&2
    echo "Quit it first:  pkill -f 'user-data-dir=$USER_DATA_DIR'" >&2
    exit 1
fi

mkdir -p "$USER_DATA_DIR"

# Background, detached, stderr-to-log so we can diagnose future startup failures.
LOG_FILE="$USER_DATA_DIR/launch.log"
"$CHROME_BIN" \
    --remote-debugging-port="$PORT" \
    --remote-allow-origins='*' \
    --user-data-dir="$USER_DATA_DIR" \
    --no-first-run \
    --no-default-browser-check \
    "$@" >"$LOG_FILE" 2>&1 &
chrome_pid=$!
disown

# Wait briefly for the CDP socket to come up, so the user knows whether the
# launch succeeded before this script exits.
for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.4
    if curl -s -m 1 -o /dev/null -w "%{http_code}" "http://localhost:$PORT/json/version" | grep -q "^200$"; then
        echo "Chrome (pid $chrome_pid) launched with CDP listening on http://localhost:$PORT"
        echo "User-data-dir: $USER_DATA_DIR (logs in $LOG_FILE)"
        echo "First-time setup: sign in to juejin / csdn / wechat-mp in this window — credentials persist for next runs."
        exit 0
    fi
done

echo "Chrome launched (pid $chrome_pid) but CDP port $PORT is not responding after 4s." >&2
echo "Check $LOG_FILE for startup errors." >&2
exit 1
