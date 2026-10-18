#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
TMP_ROOT="${TMPDIR:-$PREFIX/tmp}"
STATE_DIR="$HOME/.local/share/ternuxx/proot-display0"
STATE_FILE="$STATE_DIR/session.json"
SUPERVISOR="$ROOT/lib/desktop-supervisor.sh"
OWNED_EXEC="$ROOT/lib/owned-exec.py"
DISPLAY_VALUE=":0"
ANDROID_USER=0

usage() {
  cat <<'EOF'
Usage: proot-gui0.sh {start|status|stop} [--android-user ID]
Starts the existing Debian PRoot XFCE workload on display :0.
Uses the native Termux:X11 activity on Android user 0. The session stays alive until explicitly stopped.
EOF
}
ACTION="${1:-}"
[ "$#" -gt 0 ] && shift || true
while [ "$#" -gt 0 ]; do
  case "$1" in
    --android-user)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      ANDROID_USER="$2"; shift 2 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ "$ANDROID_USER" =~ ^[0-9]+$ ]] || { echo "invalid Android user ID" >&2; exit 2; }

read_state() {
  python3 - "$STATE_FILE" "$1" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        value = json.load(stream)
    for key in sys.argv[2].split("."):
        value = value[key]
    print(value if value is not None else "")
except (OSError, ValueError, KeyError, TypeError):
    raise SystemExit(1)
PY
}

case "$ACTION" in
  status)
    if [ ! -f "$STATE_FILE" ]; then
      echo "PRoot GUI :0 is stopped (no Ternuxx session record)."
      exit 0
    fi
    status="$(read_state status || echo unknown)"
    display="$(read_state display || echo unknown)"
    user="$(read_state android_user || echo 0)"
    printf 'PRoot GUI status=%s display=%s android_user=%s\n' "$status" "$display" "$user"
    echo "log=$STATE_DIR/desktop.log"
    ;;

  start)
    [ -x "$SUPERVISOR" ] && [ -x "$OWNED_EXEC" ] || { echo "Ternuxx supervisor files are unavailable" >&2; exit 1; }
    for tool in termux-x11 am proot-distro python3 nohup; do
      command -v "$tool" >/dev/null 2>&1 || { echo "required host command is missing: $tool" >&2; exit 1; }
    done
    [ -x "$PREFIX/bin/xfce4-session" ] || { echo "native Termux XFCE supervisor marker is missing" >&2; exit 1; }
    [ -d "$TMP_ROOT/.X11-unix" ] || { echo "Termux X11 socket directory is missing: $TMP_ROOT/.X11-unix" >&2; exit 1; }
    mkdir -p "$STATE_DIR"
    chmod 700 "$HOME/.local/share/ternuxx" "$STATE_DIR" 2>/dev/null || true
    if [ -f "$STATE_FILE" ]; then
      current="$(read_state status || echo unknown)"
      if [ "$current" = running ]; then
        echo "PRoot GUI :0 is already running; use status or stop first." >&2
        exit 1
      fi
      if [ "$current" != stopped ] && [ "$current" != failed ]; then
        echo "previous PRoot GUI state is '$current'; inspect $STATE_DIR/desktop.log before retrying." >&2
        exit 1
      fi
    fi
    if ! python3 "$ROOT/lib/x11_display.py" "$TMP_ROOT" 0; then
      echo "display :0 is occupied or cannot be safely recovered; no processes were stopped." >&2
      exit 1
    fi
    if [ "$ANDROID_USER" != 0 ]; then
      echo "Android user $ANDROID_USER is unsupported: this native Termux X server can only use the user 0 Termux:X11 activity." >&2
      echo "Use the single native Termux:X11 app; cloned-profile rendering is not supported by this launcher." >&2
      exit 1
    fi
    if ! "$PREFIX/bin/am" start --user 0 -n com.termux.x11/com.termux.x11.MainActivity >/dev/null; then
      echo "Termux:X11 activity request failed for Android user 0" >&2
      exit 1
    fi
    touch "$STATE_DIR/desktop.log"
    chmod 600 "$STATE_DIR/desktop.log"
    nohup "$SUPERVISOR" "$DISPLAY_VALUE" "$STATE_DIR" "$TMP_ROOT" \
      "$PREFIX/bin/termux-x11" "$ROOT/lib/proot-xfce-wrapper.sh" \
      "$PREFIX/bin/xfce4-session" "$OWNED_EXEC" proot-display0 \
      >> "$STATE_DIR/desktop.log" 2>&1 </dev/null &
    for _ in $(seq 1 60); do
      current="$(read_state status 2>/dev/null || true)"
      case "$current" in
        running)
          python3 - "$STATE_FILE" "$ANDROID_USER" <<'PY'
import json, os, sys, tempfile
path, user = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    state = json.load(stream)
state["android_user"] = int(user)
fd, temporary = tempfile.mkstemp(prefix=".session.", dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)
        stream.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
finally:
    try: os.unlink(temporary)
    except FileNotFoundError: pass
PY
          echo "PRoot XFCE supervisor is running on :0; Android user $ANDROID_USER activity was requested."
          echo "GUI visibility must be confirmed in the selected Termux:X11 window."
          exit 0 ;;
        failed|stop_incomplete)
          echo "PRoot GUI start failed (state=$current). Log: $STATE_DIR/desktop.log" >&2
          tail -n 50 "$STATE_DIR/desktop.log" >&2 || true
          exit 1 ;;
      esac
      sleep 0.25
    done
    echo "PRoot GUI did not become ready; inspect $STATE_DIR/desktop.log and session.json." >&2
    exit 1
    ;;

  stop)
    if [ ! -f "$STATE_FILE" ]; then
      echo "PRoot GUI :0 is stopped (no Ternuxx session record)."
      exit 0
    fi
    python3 - "$STATE_FILE" <<'PY'
import json, os, signal, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    state = json.load(stream)
role = state.get("supervisor", {})
pid, expected = role.get("pid"), role.get("start_ticks")
if not pid or not expected:
    raise SystemExit("session has no verifiable supervisor identity; refusing to signal processes")
try:
    raw = open(f"/proc/{pid}/stat", encoding="ascii").read()
    rest = raw[raw.rfind(")") + 2:].split()
    actual = rest[19]
    command = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\\0", b" ").decode(errors="replace")
except (OSError, IndexError):
    raise SystemExit("recorded supervisor is not running; inspect session.json before recovery")
if actual != str(expected) or "desktop-supervisor.sh" not in command:
    raise SystemExit("recorded PID no longer identifies this supervisor; refusing to signal it")
os.kill(int(pid), signal.SIGTERM)
PY
    for _ in $(seq 1 80); do
      current="$(read_state status || echo unknown)"
      if [ "$current" = stopped ]; then
        echo "Stopped only the PRoot GUI session owned on :0; native :1 was not targeted."
        exit 0
      fi
      sleep 0.25
    done
    echo "PRoot GUI stop did not complete. Inspect $STATE_DIR/session.json and desktop.log; no broad cleanup was run." >&2
    exit 1
    ;;

  *) usage >&2; exit 2 ;;
esac
