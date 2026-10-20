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
Usage: proot-gui0.sh {start|status|stop}
New separate :0 starts are disabled. `status` and `stop` are retained for any recorded legacy session.
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
      echo "Legacy PRoot GUI session is stopped (no Ternuxx session record)."
      exit 0
    fi
    status="$(read_state status || echo unknown)"
    display="$(read_state display || echo unknown)"
    user="$(read_state android_user || echo 0)"
    printf 'Recorded Ternuxx PRoot GUI state=%s display=%s android_user=%s (record only; live process identity unverified)\n' "$status" "$display" "$user"
    echo "log=$STATE_DIR/desktop.log"
    ;;

  start)
    echo "Separate PRoot display :0 startup is disabled. Full Debian XFCE on native Termux :1 requires the shared-display nested-X11 adapter; no package or rootfs change was made." >&2
    echo "For a single Debian GUI app on the running native desktop, use: tx mng app launch APP_ID" >&2
    exit 1
    ;;

  stop)
    if [ ! -f "$STATE_FILE" ]; then
      echo "Legacy PRoot GUI session is stopped (no Ternuxx session record)."
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
