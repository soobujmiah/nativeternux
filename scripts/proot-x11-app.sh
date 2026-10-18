#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
TMP_ROOT="${TMPDIR:-$PREFIX/tmp}"
GUEST_USER="$(PYTHONPATH="$ROOT/lib" python3 -c 'import os,proot_diagnostics; print(proot_diagnostics.resolve_ternux_guest_user(home=os.environ["HOME"], path=os.environ.get("PATH", "")))')" || {
  echo "Could not safely resolve the configured Debian PRoot user from Ternux state." >&2
  exit 1
}
DISPLAY_VALUE=""

usage() {
  cat <<'USAGE'
Usage: proot-x11-app.sh [--display :N] [--] PROGRAM [ARG ...]
Runs one GUI application from the installed Debian PRoot as a window in the
already-running native Ternuxx XFCE desktop. It never starts or stops X11/XFCE.
If PROGRAM is omitted, opens Debian's xfce4-terminal.
USAGE
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --display)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      DISPLAY_VALUE="$2"; shift 2 ;;
    --) shift; break ;;
    -h|--help) usage; exit 0 ;;
    *) break ;;
  esac
done
if [ "$#" -eq 0 ]; then
  set -- xfce4-terminal
fi
if [ -z "$DISPLAY_VALUE" ]; then
  DISPLAY_VALUE="$("$ROOT/ternuxx" status --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("status")=="running" and d.get("x11")=="yes"; print(d["display"])')" || {
    echo "Ternuxx native X11 is not reported running; start it with: ~/ternuxx/ternuxx start" >&2
    exit 1
  }
fi
if [[ ! "$DISPLAY_VALUE" =~ ^:[0-9]+$ ]]; then
  echo "unsupported X11 display: $DISPLAY_VALUE" >&2
  exit 2
fi
current_display="$("$ROOT/ternuxx" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("display", ""))')"
if [ "$DISPLAY_VALUE" != "$current_display" ]; then
  echo "display $DISPLAY_VALUE is not the active Ternuxx display ($current_display); refusing to guess another X11 session." >&2
  exit 1
fi
socket="$TMP_ROOT/.X11-unix/X${DISPLAY_VALUE#:}"
[ -S "$socket" ] || { echo "active X11 socket is missing: $socket" >&2; exit 1; }
for tool in proot-distro python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "required host command is missing: $tool" >&2; exit 1; }
done
# Verify that the installed Debian guest can reach this X server before starting a GUI app.
proot-distro login debian --shared-tmp --user "$GUEST_USER" --env "DISPLAY=$DISPLAY_VALUE" -- xdpyinfo >/dev/null
# Bring forward the matching native Termux:X11 Activity. This does not stop or restart any session.
if ! "$PREFIX/bin/am" start --user 0 -n com.termux.x11/com.termux.x11.MainActivity >/dev/null 2>&1; then
  echo "Termux:X11 Activity request was not confirmed; continuing with the already-verified live X11 display." >&2
fi
binds=()
[ ! -e /dev/kgsl-3d0 ] || binds+=(--bind /dev/kgsl-3d0:/dev/kgsl)
[ ! -d /dev/dri ] || binds+=(--bind /dev/dri)
exec proot-distro login debian --shared-tmp "${binds[@]}" --user "$GUEST_USER" \
  --env "DISPLAY=$DISPLAY_VALUE" \
  --env MESA_LOADER_DRIVER_OVERRIDE=zink \
  --env GALLIUM_DRIVER=zink \
  --env TU_DEBUG=sysmem,noconform \
  --env MESA_VK_WSI_DEBUG=sw \
  --env QT_X11_NO_MITSHM=1 \
  -- "$@"
