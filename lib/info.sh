# =============================================================================
#  nativeternux — system info
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

nt_cmd_info() {
  echo "=== NativeTernux Info ==="
  echo ""

  # Device
  echo "--- Device ---"
  echo "Model:       $(getprop ro.product.model 2>/dev/null || echo unknown)"
  echo "Manufacturer:$(getprop ro.product.manufacturer 2>/dev/null || echo unknown)"
  echo "Brand:       $(getprop ro.product.brand 2>/dev/null || echo unknown)"
  echo "Android:     $(getprop ro.build.version.release 2>/dev/null || echo unknown)"
  echo "SDK:         $(getprop ro.build.version.sdk 2>/dev/null || echo unknown)"
  echo "SoC:         $(getprop ro.board.platform 2>/dev/null || echo unknown)"
  echo "ABI:         $(getprop ro.product.cpu.abi 2>/dev/null || echo unknown)"
  echo ""

  # GPU
  echo "--- GPU ---"
  if [ -e "/dev/kgsl-3d0" ]; then
    local gpu_model; gpu_model="$(cat /sys/class/kgsl/kgsl-3d0/gpu_model 2>/dev/null || echo unknown)"
    echo "GPU: $gpu_model"
    echo "/dev/kgsl-3d0: present"
  fi
  if [ -e "/dev/dri/renderD128" ]; then
    echo "/dev/dri/renderD128: present"
  fi
  echo ""

  # Termux
  echo "--- Termux ---"
  echo "Version:     ${TERMUX_VERSION:-unknown}"
  echo "PREFIX:      ${PREFIX:-/data/data/com.termux/files/usr}"
  echo "HOME:        $HOME"
  echo ""

  # Packages
  echo "--- Key packages ---"
  for pkg in xfce4-session xfce4-panel xfwm4 thunar xfce4-terminal pulseaudio dbus-x11; do
    local status="not installed"
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
      status="installed"
    fi
    printf "  %-20s %s\n" "$pkg" "$status"
  done
  echo ""

  # Commands
  echo "--- Commands ---"
  for cmd in termux-x11 dbus-launch xauth pulseaudio vulkaninfo glxinfo; do
    local where; where="$(command -v "$cmd" 2>/dev/null || echo 'not found')"
    printf "  %-20s %s\n" "$cmd" "$where"
  done
  echo ""

  # Renderer
  echo "--- Graphics ---"
  local renderer; renderer="$(_nt_detect_renderer)"
  echo "Renderer: $renderer"
  echo ""

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object \
      "model" "$(getprop ro.product.model 2>/dev/null)" \
      "android_version" "$(getprop ro.build.version.release 2>/dev/null)" \
      "gpu" "$(cat /sys/class/kgsl/kgsl-3d0/gpu_model 2>/dev/null || echo unknown)" \
      "renderer" "$renderer" \
      "termux_version" "${TERMUX_VERSION:-unknown}"
  fi
}
