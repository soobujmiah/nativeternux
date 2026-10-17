#!/data/data/com.termux/files/usr/bin/bash
# NativeTernux-owned session supervisor. Invoked only by lib/desktop.sh.
set -u
umask 077

DISPLAY_VALUE="${1:-}"
STATE_DIR="${2:-}"
TMP_ROOT="${3:-}"
X11_BIN="${4:-}"
DBUS_LAUNCH_BIN="${5:-}"
XFCE_BIN="${6:-}"
STATE_FILE="$STATE_DIR/session.json"
X11_PID=""
X11_TICKS=""
DESKTOP_PID=""
DESKTOP_TICKS=""
STOP_REASON=""
STARTUP_FAILED=0

fail() {
  STOP_REASON="$1"
  STARTUP_FAILED=1
  cleanup
  exit 1
}

proc_ticks() {
  local pid="$1" stat rest
  [ -r "/proc/$pid/stat" ] || return 1
  IFS= read -r stat < "/proc/$pid/stat" || return 1
  rest="${stat##*) }"
  set -- $rest
  [ "$#" -ge 20 ] || return 1
  printf '%s\n' "${20}"
}

proc_cmdline() {
  local pid="$1"
  [ -r "/proc/$pid/cmdline" ] || return 1
  tr '\000' ' ' < "/proc/$pid/cmdline"
}

matches_owned_process() {
  local pid="$1" ticks="$2" marker="$3" current_ticks command
  [ -n "$pid" ] && [ -n "$ticks" ] || return 1
  current_ticks="$(proc_ticks "$pid")" || return 1
  [ "$current_ticks" = "$ticks" ] || return 1
  command="$(proc_cmdline "$pid")" || return 1
  [[ "$command" == *"$marker"* ]]
}

write_state() {
  local phase="$1" error_text="${2:-}"
  python3 - "$STATE_FILE" "$phase" "$DISPLAY_VALUE" "$$" "$(proc_ticks "$$")" \
    "$X11_PID" "$X11_TICKS" "$DESKTOP_PID" "$DESKTOP_TICKS" "$error_text" <<'PY'
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

(path, phase, display, supervisor_pid, supervisor_ticks, x11_pid, x11_ticks,
 desktop_pid, desktop_ticks, error) = sys.argv[1:]
state = {
    "schema": 1,
    "owner": "nativeternux",
    "provider": "native",
    "display": display,
    "status": phase,
    "supervisor": {"pid": int(supervisor_pid), "start_ticks": supervisor_ticks,
                   "command_marker": "desktop-supervisor.sh"},
    "x11": {"pid": int(x11_pid) if x11_pid else None, "start_ticks": x11_ticks,
            "command_marker": "termux-x11"},
    "desktop": {"pid": int(desktop_pid) if desktop_pid else None,
                "start_ticks": desktop_ticks, "command_marker": "xfce4-session"},
    "error": error or None,
    "updated_at": datetime.now(timezone.utc).isoformat(),
}
fd, temporary = tempfile.mkstemp(prefix=".session.", dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)
        stream.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
finally:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
PY
}

stop_child() {
  local pid="$1" ticks="$2" marker="$3"
  [ -n "$pid" ] || return 0
  if ! matches_owned_process "$pid" "$ticks" "$marker"; then
    return 0
  fi
  kill -TERM "$pid" 2>/dev/null || return 1
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    matches_owned_process "$pid" "$ticks" "$marker" || return 0
    sleep 0.2
  done
  return 1
}

cleanup() {
  local failed=0
  trap - TERM INT HUP
  if ! stop_child "$DESKTOP_PID" "$DESKTOP_TICKS" "xfce4-session"; then
    failed=1
  fi
  if ! stop_child "$X11_PID" "$X11_TICKS" "termux-x11"; then
    failed=1
  fi
  if [ "$failed" -ne 0 ]; then
    write_state stop_incomplete "${STOP_REASON:-owned process did not exit after SIGTERM}"
  elif [ "$STARTUP_FAILED" -eq 1 ]; then
    write_state failed "$STOP_REASON"
  else
    write_state stopped "${STOP_REASON:-}"
  fi
}

on_signal() {
  STOP_REASON="received stop signal"
  cleanup
  exit 0
}
trap on_signal TERM INT HUP

case "$DISPLAY_VALUE" in
  :[0-9]*) ;;
  *) fail "invalid display" ;;
esac
[ -d "$STATE_DIR" ] || fail "state directory missing"
[ -d "$TMP_ROOT/.X11-unix" ] || fail "Termux X11 socket directory missing"
[ -x "$X11_BIN" ] || fail "termux-x11 executable missing"
[ -x "$DBUS_LAUNCH_BIN" ] || fail "dbus-launch executable missing"
[ -x "$XFCE_BIN" ] || fail "xfce4-session executable missing"

write_state starting
"$X11_BIN" "$DISPLAY_VALUE" >> "$STATE_DIR/desktop.log" 2>&1 &
X11_PID=$!
X11_TICKS="$(proc_ticks "$X11_PID")" || fail "could not capture Termux:X11 process identity"
write_state starting

socket="$TMP_ROOT/.X11-unix/X${DISPLAY_VALUE#:}"
ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if [ -S "$socket" ]; then
    ready=1
    break
  fi
  if ! matches_owned_process "$X11_PID" "$X11_TICKS" "termux-x11"; then
    fail "Termux:X11 exited before its display socket became ready"
  fi
  sleep 0.25
done
[ "$ready" -eq 1 ] || fail "Termux:X11 display socket did not become ready"

mkdir -p "$STATE_DIR/xfce/config" "$STATE_DIR/xfce/cache" "$STATE_DIR/xfce/data" "$STATE_DIR/xfce/runtime"
chmod 700 "$STATE_DIR/xfce" "$STATE_DIR/xfce/config" "$STATE_DIR/xfce/cache" \
  "$STATE_DIR/xfce/data" "$STATE_DIR/xfce/runtime" 2>/dev/null || true
DISPLAY="$DISPLAY_VALUE" \
XDG_CONFIG_HOME="$STATE_DIR/xfce/config" \
XDG_CACHE_HOME="$STATE_DIR/xfce/cache" \
XDG_DATA_HOME="$STATE_DIR/xfce/data" \
XDG_RUNTIME_DIR="$STATE_DIR/xfce/runtime" \
  "$DBUS_LAUNCH_BIN" --exit-with-session "$XFCE_BIN" >> "$STATE_DIR/desktop.log" 2>&1 &
DESKTOP_PID=$!
DESKTOP_TICKS="$(proc_ticks "$DESKTOP_PID")" || fail "could not capture XFCE session process identity"
desktop_ready=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if matches_owned_process "$DESKTOP_PID" "$DESKTOP_TICKS" "xfce4-session"; then
    desktop_ready=1
    break
  fi
  kill -0 "$DESKTOP_PID" 2>/dev/null || fail "XFCE launcher exited before session readiness"
  sleep 0.1
done
[ "$desktop_ready" -eq 1 ] || fail "XFCE session process identity did not become verifiable"
write_state running

wait "$DESKTOP_PID"
result=$?
STOP_REASON="XFCE session exited with status $result"
cleanup
exit "$result"
