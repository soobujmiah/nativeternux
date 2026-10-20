#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
TMP_ROOT="${TMPDIR:-$PREFIX/tmp}"
GUEST_USER="$(PYTHONPATH="$ROOT/lib" python3 -c 'import os,proot_diagnostics; print(proot_diagnostics.resolve_proot_guest_user(distro="debian", prefix=os.environ["PREFIX"]))')" || {
  echo "Could not resolve one regular Debian account from the installed rootfs." >&2
  exit 1
}
DISPLAY_VALUE=""

usage() {
  cat <<'USAGE'
Usage: proot-x11-app.sh [--display :N] [--] PROGRAM [ARG ...]
Runs one GUI application from the installed Debian PRoot on a selected live X11
session. The helper uses only the Native Ternuxx-owned display and does not
invoke the separate Ternux project or its CLI.
This helper never starts or stops either desktop session.
If PROGRAM is omitted, opens Debian's xfce4-terminal.
USAGE
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --display)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      DISPLAY_VALUE="$2"; shift 2 ;;
    --session)
      echo "--session is no longer supported; Ternuxx uses its verified Native display." >&2
      exit 2 ;;
    --) shift; break ;;
    -h|--help) usage; exit 0 ;;
    *) break ;;
  esac
done
if [ "$#" -eq 0 ]; then
  set -- xfce4-terminal
fi
current_display="$("$ROOT/tx" status --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("status")=="running" and d.get("x11")=="live"; print(d["display"])')" || {
  echo "Ternuxx native X11 is not reported running; start it with: ~/ternuxx/tx start" >&2
  exit 1
}
if [ -z "$DISPLAY_VALUE" ]; then DISPLAY_VALUE="$current_display"; fi
if [ "$DISPLAY_VALUE" != "$current_display" ]; then
  echo "display $DISPLAY_VALUE is not the active Ternuxx display ($current_display); refusing to guess another X11 session." >&2
  exit 1
fi

if [[ ! "$DISPLAY_VALUE" =~ ^:[0-9]{1,2}$ ]]; then
  echo "unsupported X11 display: $DISPLAY_VALUE" >&2
  exit 2
fi
socket="$TMP_ROOT/.X11-unix/X${DISPLAY_VALUE#:}"
[ -S "$socket" ] || { echo "active X11 socket is missing: $socket" >&2; exit 1; }
for tool in proot-distro python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "required host command is missing: $tool" >&2; exit 1; }
done
# Verify that the installed Debian guest can reach this X server before starting a GUI app.
PROOT_ENV=(env -u ANDROID_ART_ROOT -u ANDROID_DATA -u ANDROID_I18N_ROOT
  -u ANDROID_ROOT -u ANDROID_RUNTIME_ROOT -u ANDROID_TZDATA_ROOT
  -u BOOTCLASSPATH -u DEX2OATBOOTCLASSPATH -u EXTERNAL_STORAGE)
"${PROOT_ENV[@]}" proot-distro login debian --shared-tmp --user "$GUEST_USER" --env "DISPLAY=$DISPLAY_VALUE" -- xdpyinfo >/dev/null
# The Ternux activity and desktop are owner-managed; never take over its UI here.
if ! "$PREFIX/bin/am" start --user 0 -n com.termux.x11/com.termux.x11.MainActivity >/dev/null 2>&1; then
  echo "Termux:X11 Activity request was not confirmed; continuing with the already-verified live X11 display." >&2
fi
if ! "$ROOT/tx" audio start >/dev/null; then
  echo "Native PulseAudio is not ready; continuing the PRoot GUI launch without audio." >&2
fi
binds=()
[ ! -e /dev/kgsl-3d0 ] || binds+=(--bind /dev/kgsl-3d0:/dev/kgsl)
[ ! -d /dev/dri ] || binds+=(--bind /dev/dri)
pulse_args=()
pulse_cookie="$(PYTHONPATH="$ROOT/lib" python3 -c 'import proot_diagnostics; p=proot_diagnostics._native_pulse_cookie_path(); print(p or "")')" || pulse_cookie=""
if [ -n "$pulse_cookie" ]; then
  pulse_args+=(--bind "$pulse_cookie:/tmp/.ternuxx-pulse-cookie" --env PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie)
fi
exec "${PROOT_ENV[@]}" proot-distro login debian --shared-tmp "${binds[@]}" "${pulse_args[@]}" --user "$GUEST_USER" --env "DISPLAY=$DISPLAY_VALUE" --env PULSE_SERVER=tcp:127.0.0.1:4713 --env MESA_LOADER_DRIVER_OVERRIDE=zink --env GALLIUM_DRIVER=zink --env TU_DEBUG=sysmem,noconform --env MESA_VK_WSI_DEBUG=sw --env MESA_SHADER_CACHE_DISABLE=true --env QT_X11_NO_MITSHM=1 -- "$@"
