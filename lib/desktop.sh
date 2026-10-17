# NativeTernux native desktop lifecycle.
# Owns only the supervisor and exact child processes recorded in session.json.
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

_nt_session_file() { printf '%s/session.json\n' "$NATIVERNUX_STATE_DIR"; }
_nt_session_lock() { printf '%s/.session.lock\n' "$NATIVERNUX_STATE_DIR"; }

_nt_state_value() {
  local key="$1" file
  file="$(_nt_session_file)"
  [ -f "$file" ] || return 1
  python3 - "$file" "$key" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        value = json.load(stream)
    current = value
    for part in sys.argv[2].split("."):
        current = current[part]
    if current is None:
        raise SystemExit(1)
    print(current)
except (OSError, ValueError, KeyError, TypeError):
    raise SystemExit(1)
PY
}

_nt_proc_start_ticks() {
  local pid="$1" stat rest
  [ -r "/proc/$pid/stat" ] || return 1
  IFS= read -r stat < "/proc/$pid/stat" || return 1
  rest="${stat##*) }"
  set -- $rest
  [ "$#" -ge 20 ] || return 1
  printf '%s\n' "${20}"
}

_nt_proc_matches() {
  local pid="$1" expected_ticks="$2" marker="$3" actual_ticks command
  [ -n "$pid" ] && [ -n "$expected_ticks" ] || return 1
  actual_ticks="$(_nt_proc_start_ticks "$pid")" || return 1
  [ "$actual_ticks" = "$expected_ticks" ] || return 1
  [ -r "/proc/$pid/cmdline" ] || return 1
  command="$(tr '\000' ' ' < "/proc/$pid/cmdline")"
  [[ "$command" == *"$marker"* ]]
}

_nt_state_process_live() {
  local role="$1" pid ticks marker
  pid="$(_nt_state_value "$role.pid")" || return 1
  ticks="$(_nt_state_value "$role.start_ticks")" || return 1
  marker="$(_nt_state_value "$role.command_marker")" || return 1
  _nt_proc_matches "$pid" "$ticks" "$marker"
}

_nt_owned_stop() {
  local role="$1" pid ticks marker
  pid="$(_nt_state_value "$role.pid")" || return 0
  ticks="$(_nt_state_value "$role.start_ticks")" || return 0
  marker="$(_nt_state_value "$role.command_marker")" || return 0
  [ "$pid" != "None" ] && [ -n "$pid" ] || return 0
  if ! _nt_proc_matches "$pid" "$ticks" "$marker"; then
    return 0
  fi
  kill -TERM "$pid" 2>/dev/null || return 1
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    _nt_proc_matches "$pid" "$ticks" "$marker" || return 0
    sleep 0.2
  done
  return 1
}

_nt_display_available() {
  local number="$1" tmp_root="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
  [ ! -e "$tmp_root/.X11-unix/X$number" ] || return 1
  [ ! -e "$tmp_root/.X$number-lock" ] || return 1
}

_nt_state_path_is_private() {
  python3 - "$HOME" "$NATIVERNUX_STATE_DIR" <<'PY'
import os, sys
home = os.path.realpath(sys.argv[1])
state = os.path.realpath(sys.argv[2])
raise SystemExit(0 if state.startswith(home.rstrip(os.sep) + os.sep) else 1)
PY
}

_nt_session_active() {
  [ -f "$(_nt_session_file)" ] || return 1
  _nt_state_process_live supervisor
}

nt_cmd_start() {
  local display_number="" arg state_root supervisor log_file tmp_root
  while [ $# -gt 0 ]; do
    arg="$1"; shift
    case "$arg" in
      --display)
        [ $# -gt 0 ] || { nt_fail "--display needs a number"; return 2; }
        display_number="${1#:}"; shift
        [[ "$display_number" =~ ^[0-9]{1,2}$ ]] || { nt_fail "Invalid display number"; return 2; }
        ;;
      *) nt_fail "Unknown start option: $arg"; return 2 ;;
    esac
  done

  nt_require_termux || return 1
  for tool in termux-x11 dbus-launch xfce4-session python3 nohup; do
    nt_require_command "$tool" || return 1
  done
  supervisor="$_TN_LIB_DIR/desktop-supervisor.sh"
  [ -x "$supervisor" ] || { nt_fail "NativeTernux session supervisor is missing"; return 1; }

  state_root="$NATIVERNUX_STATE_DIR"
  _nt_state_path_is_private || { nt_fail "State path must resolve inside Termux HOME"; return 1; }
  mkdir -p "$state_root" || { nt_fail "Cannot create NativeTernux state directory"; return 1; }
  chmod 700 "$state_root" 2>/dev/null || { nt_fail "Cannot protect NativeTernux state directory"; return 1; }

  if _nt_session_active; then
    nt_ok "NativeTernux desktop is already running."
    nt_info "Display: $(_nt_state_value display)"
    return 0
  fi
  if [ -f "$(_nt_session_file)" ]; then
    local previous
    previous="$(_nt_state_value status 2>/dev/null || printf unknown)"
    case "$previous" in
      stopped) ;;
      *) nt_fail "A prior NativeTernux session is not verifiably stopped (state: $previous). Inspect its log and session state before starting again."; return 1 ;;
    esac
  fi

  state_root="$NATIVERNUX_STATE_DIR"
  local lock
  lock="$(_nt_session_lock)"
  if ! mkdir "$lock" 2>/dev/null; then
    nt_fail "Another NativeTernux lifecycle operation holds the session lock. If no operation is running, inspect and recover the lock manually."; return 1
  fi
  # This CLI process handles exactly one command, so EXIT scopes lock cleanup
  # to the full lifecycle operation (RETURN would release it inside helpers).
  trap 'rmdir "$lock" 2>/dev/null || true' EXIT

  tmp_root="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
  if [ -z "$display_number" ]; then
    for display_number in $(seq 0 10); do
      _nt_display_available "$display_number" && break
    done
    _nt_display_available "$display_number" || { nt_fail "No free Termux:X11 display found"; return 1; }
  else
    _nt_display_available "$display_number" || { nt_fail "Display :$display_number has a socket or lock; refusing to reuse it"; return 1; }
  fi

  log_file="$state_root/desktop.log"
  touch "$log_file" || { nt_fail "Cannot create the NativeTernux desktop log"; return 1; }
  chmod 600 "$log_file" 2>/dev/null || true
  rm -f "$state_root/session.ready" 2>/dev/null || true
  nt_step "Starting NativeTernux-owned X11 and XFCE on :$display_number..."
  nohup "$supervisor" ":$display_number" "$state_root" "$tmp_root" \
    "$(command -v termux-x11)" "$(command -v dbus-launch)" \
    "$(command -v xfce4-session)" >> "$log_file" 2>&1 </dev/null &

  local ready=0 result
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    result="$(_nt_state_value status 2>/dev/null || true)"
    if [ "$result" = "running" ]; then
      ready=1
      break
    fi
    if [ "$result" = "failed" ] || [ "$result" = "stop_incomplete" ]; then
      nt_fail "Desktop startup failed (state: $result). Review $log_file and session.json; no unrelated process was stopped."
      return 1
    fi
    sleep 0.25
  done
  if [ "$ready" -ne 1 ]; then
    local pid ticks
    pid="$(_nt_state_value supervisor.pid 2>/dev/null || true)"
    ticks="$(_nt_state_value supervisor.start_ticks 2>/dev/null || true)"
    if _nt_proc_matches "$pid" "$ticks" "desktop-supervisor.sh"; then
      kill -TERM "$pid" 2>/dev/null || true
      for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        _nt_proc_matches "$pid" "$ticks" "desktop-supervisor.sh" || break
        sleep 0.2
      done
    fi
    nt_fail "Desktop did not report ready within 7.5 seconds. Inspect $log_file and session.json; do not delete sockets or kill untracked processes."
    return 1
  fi

  nt_ok "NativeTernux desktop session is running on :$display_number."
  nt_info "Open the Termux:X11 Android app to view it; activity visibility is not inferred from server readiness."
  nt_info "NativeTernux does not start or stop PulseAudio; existing audio services remain independently owned."
  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object "start" "running" "display" ":$display_number" "gui_visible" "unknown" "audio_owner" "external"
  fi
}

nt_cmd_stop() {
  local file status supervisor_pid supervisor_ticks lock
  file="$(_nt_session_file)"
  if [ ! -f "$file" ]; then
    nt_info "No NativeTernux session record exists; no processes were inspected or stopped."
    return 0
  fi

  lock="$(_nt_session_lock)"
  if ! mkdir "$lock" 2>/dev/null; then
    nt_fail "Another NativeTernux lifecycle operation holds the session lock. If no operation is running, inspect and recover the lock manually."
    return 1
  fi
  trap 'rmdir "$lock" 2>/dev/null || true' EXIT

  status="$(_nt_state_value status 2>/dev/null || printf unknown)"
  supervisor_pid="$(_nt_state_value supervisor.pid 2>/dev/null || true)"
  supervisor_ticks="$(_nt_state_value supervisor.start_ticks 2>/dev/null || true)"

  if [ -n "$supervisor_pid" ] && _nt_proc_matches "$supervisor_pid" "$supervisor_ticks" "desktop-supervisor.sh"; then
    nt_step "Stopping the recorded NativeTernux session supervisor..."
    kill -TERM "$supervisor_pid" 2>/dev/null || { nt_fail "Could not signal the verified session supervisor"; return 1; }
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
      status="$(_nt_state_value status 2>/dev/null || true)"
      [ "$status" = "stopped" ] && break
      [ "$status" = "stop_incomplete" ] && break
      _nt_proc_matches "$supervisor_pid" "$supervisor_ticks" "desktop-supervisor.sh" || break
      sleep 0.2
    done
  else
    nt_warn "Supervisor is not live with its recorded identity; checking only its exact recorded desktop/X11 child PIDs."
    local failures=0
    _nt_owned_stop desktop || failures=1
    _nt_owned_stop x11 || failures=1
    if [ "$failures" -eq 0 ]; then
      python3 - "$file" <<'PY'
import json, os, sys, tempfile
from datetime import datetime, timezone
path=sys.argv[1]
with open(path, encoding="utf-8") as stream: state=json.load(stream)
state["status"]="stopped"
state["updated_at"]=datetime.now(timezone.utc).isoformat()
fd,tmp=tempfile.mkstemp(prefix=".session.",dir=os.path.dirname(path))
try:
    with os.fdopen(fd,"w",encoding="utf-8") as stream:
        json.dump(state,stream,indent=2); stream.write("\n")
    os.chmod(tmp,0o600); os.replace(tmp,path)
finally:
    try: os.unlink(tmp)
    except FileNotFoundError: pass
PY
      status=stopped
    fi
  fi

  case "$status" in
    stopped)
      nt_ok "NativeTernux-owned desktop processes stopped. Session record and log were retained."
      [ "$NATIVERNUX_JSON" = "1" ] && nt_json_object "stop" "stopped" "owner" "nativeternux"
      return 0 ;;
    stop_incomplete)
      nt_fail "An owned process did not exit cleanly. State and log are retained; no SIGKILL or broad cleanup was used."
      return 1 ;;
    *)
      nt_fail "Stop result is not confirmed (state: ${status:-unknown}). Review the session record and log."
      return 1 ;;
  esac
}

nt_cmd_restart() {
  nt_cmd_stop || return $?
  nt_cmd_start "$@"
}

nt_cmd_status() {
  local file status display supervisor_live x11_live desktop_live
  file="$(_nt_session_file)"
  if [ ! -f "$file" ]; then
    status=stopped; display=none; supervisor_live=no; x11_live=no; desktop_live=no
  else
    status="$(_nt_state_value status 2>/dev/null || printf unknown)"
    display="$(_nt_state_value display 2>/dev/null || printf unknown)"
    _nt_state_process_live supervisor && supervisor_live=yes || supervisor_live=no
    _nt_state_process_live x11 && x11_live=yes || x11_live=no
    _nt_state_process_live desktop && desktop_live=yes || desktop_live=no
    if [ "$status" = "running" ] && { [ "$supervisor_live" != yes ] || [ "$x11_live" != yes ] || [ "$desktop_live" != yes ]; }; then
      status=degraded
    fi
  fi

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object "status" "$status" "display" "$display" \
      "supervisor" "$supervisor_live" "x11" "$x11_live" \
      "xfce4_session" "$desktop_live" "gui_visible" "unknown" \
      "audio_owner" "external"
  else
    printf '  %-18s %s\n' "NativeTernux:" "$status"
    printf '  %-18s %s\n' "Display:" "$display"
    printf '  %-18s %s\n' "Supervisor:" "$supervisor_live"
    printf '  %-18s %s\n' "Termux:X11:" "$x11_live"
    printf '  %-18s %s\n' "XFCE session:" "$desktop_live"
    printf '  %-18s %s\n' "GUI visible:" "unknown (open/check Termux:X11)"
    printf '  %-18s %s\n' "Audio owner:" "external (not managed)"
  fi
}
