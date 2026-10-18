#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
expected="${PREFIX:-/data/data/com.termux/files/usr}/bin/xfce4-session"
if [[ "$#" -ne 2 || "$1" != "--exit-with-session" || "$2" != "$expected" ]]; then
  echo "refusing unsupported PRoot desktop command" >&2
  exit 64
fi
exec proot-distro login debian --shared-tmp \
  --bind /dev/kgsl-3d0:/dev/kgsl --bind /dev/dri --user sbj \
  --env DISPLAY=:0 \
  --env TERNUXX_SESSION_ID=proot-display0 \
  --env MESA_LOADER_DRIVER_OVERRIDE=zink \
  --env GALLIUM_DRIVER=zink \
  --env TU_DEBUG=sysmem,noconform \
  --env MESA_VK_WSI_DEBUG=sw \
  --env MESA_DISK_CACHE_SINGLE_FILE=1 \
  --env MESA_SHADER_CACHE_MAX_SIZE=2048M \
  --env QT_X11_NO_MITSHM=1 \
  --env XDG_CONFIG_HOME=/home/sbj/.local/share/ternuxx/proot-display0/xfce/config \
  --env XDG_CACHE_HOME=/home/sbj/.local/share/ternuxx/proot-display0/xfce/cache \
  --env XDG_DATA_HOME=/home/sbj/.local/share/ternuxx/proot-display0/xfce/data \
  --env XDG_RUNTIME_DIR=/home/sbj/.local/share/ternuxx/proot-display0/xfce/runtime \
  --env LANG=en_US.UTF-8 --env LC_ALL=en_US.UTF-8 \
  -- bash -lc '
    set -eu
    state="$HOME/.local/share/ternuxx/proot-display0/xfce"
    mkdir -p "$state/config" "$state/cache" "$state/data" "$state/runtime"
    chmod 700 "$state" "$state/config" "$state/cache" "$state/data" "$state/runtime"
    export XDG_CONFIG_HOME="$state/config" XDG_CACHE_HOME="$state/cache"
    export XDG_DATA_HOME="$state/data" XDG_RUNTIME_DIR="$state/runtime"
    exec dbus-launch --exit-with-session startxfce4
  '
