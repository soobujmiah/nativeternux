#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
TMP_ROOT="${TMPDIR:-$PREFIX/tmp}"
STATE_DIR="$HOME/.local/share/ternuxx/proot-display0"
NATIVE_STATE="${TERNUXX_STATE_DIR:-$HOME/.local/share/ternuxx}"
discovered_state="$(python3 "$ROOT/lib/desktop_session_discovery.py" "$ROOT/lib/desktop-supervisor.sh" "$HOME" "$NATIVE_STATE" 2>/dev/null || true)"
[ -z "$discovered_state" ] || NATIVE_STATE="$discovered_state"
STATE_FILE="$STATE_DIR/session.json"
SUPERVISOR="$ROOT/lib/desktop-supervisor.sh"
WRAPPER="$ROOT/lib/proot-xfce-wrapper.sh"
OWNED_EXEC="$ROOT/lib/owned-exec.py"
STATE_HELPER="$ROOT/lib/desktop_session_state.py"
DISPLAY_TOOL="$ROOT/lib/x11_display.py"
ACTION="${1:-status}"
shift || true
MODE=auto
if [ "$ACTION" = start ]; then
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --mode) [ "$#" -ge 2 ] || { echo "--mode needs auto|standalone|nested" >&2; exit 2; }; MODE="$2"; shift 2 ;;
      --help|-h) ACTION=help; shift ;;
      *) echo "Unknown pgui start option: $1" >&2; exit 2 ;;
    esac
  done
fi

usage() { cat <<'USAGE'
Usage: tx pgui [start [--mode auto|standalone|nested]|status|stop]
Auto uses standalone :0 when Native GUI is stopped, otherwise nested Xephyr :2 inside Native :1.
Standalone and Native desktop sessions cannot run together. Nested mode holds the lifecycle lock until closed.
USAGE
}

inspect() { python3 "$STATE_HELPER" inspect "$HOME" "$STATE_DIR" /proc "$TMP_ROOT"; }
json_state() { python3 -c 'import json,sys; print(json.load(sys.stdin).get("state","unknown"))' <<<"$1" 2>/dev/null || printf '%s\n' "${2:-unknown}"; }
state_value() { python3 - "$STATE_FILE" "$1" <<'PY'
import json,sys
try:
    value=json.load(open(sys.argv[1],encoding="utf-8"))
    for key in sys.argv[2].split("."):
        value=value[key]
    print("" if value is None else value)
except (OSError,ValueError,KeyError,TypeError):
    raise SystemExit(1)
PY
}

case "$ACTION" in
  help) usage ;;
  status)
    native_report="$(python3 "$STATE_HELPER" inspect "$HOME" "$NATIVE_STATE" /proc "$TMP_ROOT" 2>/dev/null || true)"
    native_state="$(json_state "$native_report" unknown)"
    printf 'Native desktop: %s\n' "$native_state"
    if [ ! -e "$STATE_FILE" ]; then
      echo "Standalone Debian GUI: stopped; target display :0"
    else
      report="$(inspect)" || { echo "PRoot GUI ownership is unknown or unsafe; state preserved." >&2; exit 1; }
      python3 -c 'import json,sys; d=json.load(sys.stdin); print("Standalone Debian GUI: state={state} display={display} detail={detail}".format(state=d.get("state"),display=d.get("display",":0"),detail=d.get("reason","unknown")))' <<<"$report"
    fi
    if [ -S "$TMP_ROOT/.X11-unix/X2" ]; then
      echo "Nested display :2 socket exists; socket presence alone does not establish session ownership."
    else
      echo "Nested display :2 socket is absent."
    fi
    ;;

  start)
    [[ "$MODE" = auto || "$MODE" = standalone || "$MODE" = nested ]] || { echo "--mode must be auto, standalone, or nested." >&2; exit 2; }
    python3 "$STATE_HELPER" ensure-state "$HOME" "$NATIVE_STATE" >/dev/null
    python3 "$STATE_HELPER" ensure-state "$HOME" "$STATE_DIR" >/dev/null
    GLOBAL_LOCK="$NATIVE_STATE/.session.lock"
    LOCAL_LOCK="$STATE_DIR/.session.lock"
    mkdir "$GLOBAL_LOCK" 2>/dev/null || { echo "Another Ternuxx desktop lifecycle operation is active; retry after it finishes." >&2; exit 1; }
    global_lock=1; local_lock=0
    release_locks() { [ "$local_lock" -eq 0 ] || rmdir "$LOCAL_LOCK" 2>/dev/null || true; [ "$global_lock" -eq 0 ] || rmdir "$GLOBAL_LOCK" 2>/dev/null || true; }
    trap release_locks EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    native_report="$(python3 "$STATE_HELPER" inspect "$HOME" "$NATIVE_STATE" /proc "$TMP_ROOT")" || { echo "Native GUI ownership is unknown; refusing PRoot GUI startup." >&2; exit 1; }
    native_state="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("state","unknown"))' <<<"$native_report")"
    [ "$MODE" != auto ] || { [ "$native_state" = running ] && MODE=nested || MODE=standalone; }
    if [ "$MODE" = nested ]; then
      [ "$native_state" = running ] || { echo "Nested PRoot GUI requires the verified Native desktop to be running." >&2; exit 1; }
      native_display="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("display",""))' <<<"$native_report")"
      [ "$native_display" = :1 ] || { echo "Nested PRoot GUI currently requires Native display :1; found $native_display." >&2; exit 1; }
      PYTHONPATH="$ROOT/lib" python3 -c 'import os,proot_diagnostics; proot_diagnostics.resolve_proot_guest_shell(distro="debian",user="sbj",prefix=os.environ["PREFIX"])' >/dev/null 2>&1 || { echo "The existing Debian PRoot user profile is unavailable; no setup changes were made." >&2; exit 1; }
      "$ROOT/tx" audio start >/dev/null || { echo "Ternuxx Native PulseAudio could not be made ready; no Debian GUI was started." >&2; exit 1; }
      cookie="$(PYTHONPATH="$ROOT/lib" python3 -c 'import proot_diagnostics; print(proot_diagnostics._native_pulse_cookie_path() or "")' 2>/dev/null)"
      [ -n "$cookie" ] && [ -f "$cookie" ] && [ ! -L "$cookie" ] || { echo "Ternuxx Native PulseAudio cookie is unavailable; no PRoot GUI was started." >&2; exit 1; }
      guest_script=$(cat <<'GUEST'
set -eu
state="$HOME/.local/share/ternuxx/proot-nested-gui"
mkdir -p "$state" "$state/config/xfce4/xfconf/xfce-perchannel-xml" "$state/cache" "$state/data" "$state/runtime"
chmod 700 "$state" "$state/config" "$state/cache" "$state/data" "$state/runtime"
export XDG_CONFIG_HOME="$state/config" XDG_CACHE_HOME="$state/cache" XDG_DATA_HOME="$state/data" XDG_RUNTIME_DIR="$state/runtime"
printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' '<channel name="xfwm4" version="1.0"><property name="general" type="empty"><property name="use_compositing" type="bool" value="false"/></property></channel>' > "$XDG_CONFIG_HOME/xfce4/xfconf/xfce-perchannel-xml/xfwm4.xml"
/usr/bin/Xephyr :2 -glamor_gles2 -screen 1280x720 -resizeable -no-host-grab -nolisten tcp >"$state/xephyr.log" 2>&1 &
xephyr_pid=$!
xfce_pid=
cleanup() {
  [ -z "$xfce_pid" ] || kill -TERM "$xfce_pid" 2>/dev/null || true
  [ -z "$xfce_pid" ] || wait "$xfce_pid" 2>/dev/null || true
  kill -TERM "$xephyr_pid" 2>/dev/null || true
  wait "$xephyr_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
ready=0
for _ in $(seq 1 80); do
  if DISPLAY=:2 xdpyinfo >/dev/null 2>&1; then ready=1; break; fi
  kill -0 "$xephyr_pid" 2>/dev/null || break
  sleep 0.25
done
[ "$ready" -eq 1 ] || { echo "Xephyr :2 did not become ready; see $state/xephyr.log" >&2; exit 1; }
renderer="$(DISPLAY=:2 es2_info 2>/dev/null | sed -n 's/^GL_RENDERER: //p' | head -n 1 || true)"
printf 'Nested Debian XFCE display :2 is ready; GLES renderer: %s\n' "${renderer:-unreported}"
DISPLAY=:2 dbus-launch --exit-with-session startxfce4 &
xfce_pid=$!
wait "$xfce_pid"
GUEST
)
      args=(login debian --shared-tmp --user sbj
        --bind "$cookie:/tmp/.ternuxx-pulse-cookie"
        --env DISPLAY=:1 --env PULSE_SERVER=tcp:127.0.0.1:4713 --env PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie
        --env GALLIUM_DRIVER=zink --env MESA_LOADER_DRIVER_OVERRIDE=zink
        --env TU_DEBUG=sysmem,noconform --env MESA_VK_WSI_DEBUG=sw
        --env MESA_DISK_CACHE_SINGLE_FILE=1 --env MESA_SHADER_CACHE_MAX_SIZE=2048M
        --env QT_X11_NO_MITSHM=1 --env LANG=en_US.UTF-8 --env LC_ALL=en_US.UTF-8)
      [ ! -c /dev/kgsl-3d0 ] || args+=(--bind /dev/kgsl-3d0:/dev/kgsl)
      [ ! -d /dev/dri ] || args+=(--bind /dev/dri)
      args+=(-- /usr/bin/env DISPLAY=:1 PULSE_SERVER=tcp:127.0.0.1:4713 PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie
        GALLIUM_DRIVER=zink MESA_LOADER_DRIVER_OVERRIDE=zink TU_DEBUG=sysmem,noconform MESA_VK_WSI_DEBUG=sw
        MESA_DISK_CACHE_SINGLE_FILE=1 MESA_SHADER_CACHE_MAX_SIZE=2048M QT_X11_NO_MITSHM=1 LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
        /bin/bash -c "$guest_script")
      echo "Starting full Debian XFCE nested in Native :1 through Xephyr :2. Press Ctrl-C in this terminal to close only the nested desktop."
      env -u DBUS_SESSION_BUS_ADDRESS -u DBUS_SESSION_BUS_PID -u DBUS_STARTER_ADDRESS -u DBUS_STARTER_BUS_TYPE -u ANDROID_ART_ROOT -u ANDROID_DATA -u ANDROID_I18N_ROOT -u ANDROID_ROOT -u ANDROID_RUNTIME_ROOT -u ANDROID_TZDATA_ROOT -u BOOTCLASSPATH -u DEX2OATBOOTCLASSPATH -u EXTERNAL_STORAGE -u LD_LIBRARY_PATH -u LD_PRELOAD "$PREFIX/bin/proot-distro" "${args[@]}"
      exit $?
    fi
    [ "$native_state" = stopped ] || { echo "Standalone display :0 requires Native GUI stopped; current Native state is $native_state. Choose nested mode while Native GUI is running." >&2; exit 1; }
    [ -x "$SUPERVISOR" ] && [ -x "$WRAPPER" ] && [ -x "$ROOT/lib/proot-dbus-session.sh" ] && [ -x "$OWNED_EXEC" ] || { echo "Ternuxx PRoot desktop component is unavailable." >&2; exit 1; }
    PYTHONPATH="$ROOT/lib" python3 -c 'import os,proot_diagnostics; proot_diagnostics.resolve_proot_guest_shell(distro="debian",user="sbj",prefix=os.environ["PREFIX"])' >/dev/null 2>&1 || { echo "The existing Debian PRoot user profile is unavailable; no setup changes were made." >&2; exit 1; }
    mkdir "$LOCAL_LOCK" 2>/dev/null || { echo "Another standalone PRoot GUI operation is active." >&2; exit 1; }
    local_lock=1
    current="$(inspect 2>/dev/null || true)"
    current_state="$(json_state "$current" unknown)"
    if [ "$current_state" = running ]; then
      echo "Ternuxx standalone PRoot GUI is already running on :0."
      exit 0
    fi
    case "$current_state" in
      stopped) ;;
      stale)
        old_x11="$(state_value x11.pid)"
        python3 "$STATE_HELPER" reconcile-stale "$HOME" "$STATE_DIR" /proc "$TMP_ROOT" >/dev/null || { echo "Stale PRoot GUI identity changed; no display files were touched." >&2; exit 1; }
        recovery="$(python3 "$DISPLAY_TOOL" recover "$TMP_ROOT" 0 "$old_x11")" || { echo "The exact stale :0 socket/lock pair could not be safely recovered; no new server started." >&2; exit 1; }
        [ "$recovery" = recovered ] || [ "$recovery" = available ] || { echo "Display :0 recovery returned $recovery; refusing startup." >&2; exit 1; }
        cp -p "$STATE_FILE" "$STATE_DIR/session.recovered.$(date +%s).json"
        chmod 600 "$STATE_DIR"/session.recovered.*.json
        ;;
      starting|stopping|failed|unknown|unsafe|*) echo "Standalone PRoot GUI state is $current_state; inspect the session record and log. No process was signaled." >&2; exit 1 ;;
    esac
    display_state="$(python3 "$DISPLAY_TOOL" "$TMP_ROOT" 0)" || display_state=busy
    [ "$display_state" = available ] || { echo "Display :0 is $display_state; refusing to start another X server." >&2; exit 1; }
    "$ROOT/tx" audio start >/dev/null || { echo "Ternuxx Native PulseAudio could not be made ready; no Debian GUI was started." >&2; exit 1; }
    cookie="${TERNUXX_PULSE_COOKIE:-$(PYTHONPATH="$ROOT/lib" python3 -c 'import proot_diagnostics; print(proot_diagnostics._native_pulse_cookie_path() or "")' 2>/dev/null)}"
    [ -f "$cookie" ] && [ ! -L "$cookie" ] || { echo "Ternuxx Native PulseAudio cookie is unavailable; no PRoot GUI was started." >&2; exit 1; }
    touch "$STATE_DIR/desktop.log"; chmod 600 "$STATE_DIR/desktop.log"
    nohup env TERNUXX_PULSE_COOKIE="$cookie" "$SUPERVISOR" ":0" "$STATE_DIR" "$TMP_ROOT" \
      "$PREFIX/bin/termux-x11" "$ROOT/lib/proot-dbus-session.sh" "$WRAPPER" "$OWNED_EXEC" \
      proot-display0 proot >>"$STATE_DIR/desktop.log" 2>&1 </dev/null &
    ready=0
    for _ in $(seq 1 80); do
      report="$(inspect 2>/dev/null || true)"
      current_state="$(json_state "$report" unknown)"
      if [ "$current_state" = running ]; then ready=1; break; fi
      case "$current_state" in failed|unsafe|unknown) break ;; esac
      sleep 0.25
    done
    [ "$ready" -eq 1 ] || { echo "PRoot GUI did not become ready on :0. Inspect $STATE_DIR/desktop.log; no unrelated process was stopped." >&2; exit 1; }
    echo "Ternuxx-owned Debian XFCE is running on standalone display :0. Open Termux:X11 to view it."
    echo "Graphics: Debian Zink/Turnip is configured per guest process; verify with 'tx mng graphics verify debian opengl :0'."
    echo "Audio: uses the authenticated Ternuxx Native PulseAudio client endpoint; the server remains Native-owned."
    ;;

  stop)
    [ "$#" -eq 0 ] || { usage >&2; exit 2; }
    [ -f "$STATE_FILE" ] || { echo "Ternuxx standalone PRoot GUI is stopped."; exit 0; }
    python3 "$STATE_HELPER" ensure-state "$HOME" "$NATIVE_STATE" >/dev/null
    GLOBAL_LOCK="$NATIVE_STATE/.session.lock"
    LOCAL_LOCK="$STATE_DIR/.session.lock"
    mkdir "$GLOBAL_LOCK" 2>/dev/null || { echo "Another Ternuxx desktop lifecycle operation is active; retry after it finishes." >&2; exit 1; }
    global_lock=1; local_lock=0
    release_locks() { [ "$local_lock" -eq 0 ] || rmdir "$LOCAL_LOCK" 2>/dev/null || true; [ "$global_lock" -eq 0 ] || rmdir "$GLOBAL_LOCK" 2>/dev/null || true; }
    trap release_locks EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    mkdir "$LOCAL_LOCK" 2>/dev/null || { echo "Another standalone PRoot GUI operation is active." >&2; exit 1; }
    local_lock=1
    report="$(inspect)" || { echo "PRoot GUI ownership is unknown or unsafe; no signal was sent." >&2; exit 1; }
    current_state="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("state","unknown"))' <<<"$report")"
    [ "$current_state" = running ] || { echo "PRoot GUI is $current_state; stop sent no signal and preserved all state." >&2; exit 1; }
    pid="$(state_value supervisor.pid)"; ticks="$(state_value supervisor.start_ticks)"
    python3 - "$pid" "$ticks" <<'PY'
import sys
from pathlib import Path
pid,ticks=sys.argv[1:]
try:
 raw=Path(f"/proc/{pid}/stat").read_text(); fields=raw[raw.rfind(")")+2:].split()
 cmd=Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0",b" ").decode(errors="replace")
 if fields[19] != ticks or "desktop-supervisor.sh" not in cmd:
  raise SystemExit("supervisor PID identity mismatch")
except (OSError,IndexError):
 raise SystemExit("supervisor identity is unavailable")
PY
    kill -TERM "$pid"
    for _ in $(seq 1 80); do
      report="$(inspect 2>/dev/null || true)"
      current_state="$(json_state "$report" unknown)"
      [ "$current_state" = stopped ] && { echo "Stopped only the verified Debian PRoot GUI session on :0; Native :1 and Native audio were left running."; exit 0; }
      sleep 0.25
    done
    echo "PRoot GUI stop did not complete. Inspect $STATE_DIR/session.json and desktop.log; no broad cleanup was run." >&2
    exit 1
    ;;
  *) usage >&2; exit 2 ;;
esac
