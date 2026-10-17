# =============================================================================
#  nativeternux — device check / doctor
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"
# shellcheck source=lib/desktop.sh
. "$(dirname "${BASH_SOURCE[0]}")/desktop.sh"

nt_cmd_check() {
  nt_step "Checking device readiness..."

  local rc=0 missing=()

  # --- Required commands ------------------------------------------------
  for cmd in bash getprop termux-x11 dbus-launch xauth; do
    if command -v "$cmd" >/dev/null 2>&1; then
      nt_ok "$cmd: available"
    else
      nt_fail "$cmd: MISSING"
      missing+=("$cmd")
      rc=1
    fi
  done

  # --- Termux:X11 app ---------------------------------------------------
  if [ -f "/data/data/com.termux/files/usr/bin/termux-x11" ]; then
    nt_ok "Termux:X11 binary: present"
  else
    nt_warn "Termux:X11 binary: not found (app may not be installed)"
    missing+=("termux-x11-app")
    rc=1
  fi

  # --- XFCE4 packages ---------------------------------------------------
  local xfce_pkgs=("xfce4-session" "xfce4-panel" "xfwm4" "thunar" "xfce4-terminal")
  for pkg in "${xfce_pkgs[@]}"; do
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
      nt_ok "Package $pkg: installed"
    else
      nt_warn "Package $pkg: NOT installed"
      missing+=("$pkg")
      rc=1
    fi
  done

  # --- Audio ------------------------------------------------------------
  if command -v pulseaudio >/dev/null 2>&1; then
    nt_ok "pulseaudio: available"
  else
    nt_warn "pulseaudio: NOT installed"
    missing+=("pulseaudio")
    rc=1
  fi

  # --- GPU / Vulkan -----------------------------------------------------
  if command -v vulkaninfo >/dev/null 2>&1; then
    nt_ok "vulkaninfo: available"
  else
    nt_warn "vulkaninfo: NOT available"
  fi

  if command -v glxinfo >/dev/null 2>&1; then
    local renderer; renderer="$(_nt_detect_renderer)"
    nt_ok "glxinfo: available (renderer: $renderer)"
  else
    nt_warn "glxinfo: NOT available (GPU verification deferred)"
  fi

  # --- GPU device nodes -------------------------------------------------
  if [ -e "/dev/kgsl-3d0" ]; then
    local gpu_model; gpu_model="$(cat /sys/class/kgsl/kgsl-3d0/gpu_model 2>/dev/null || echo 'unknown')"
    nt_ok "GPU: $gpu_model (/dev/kgsl-3d0 present)"
  elif [ -e "/dev/dri/renderD128" ]; then
    nt_ok "GPU: /dev/dri/renderD128 present (no kgsl)"
  else
    nt_warn "GPU device nodes: none found (/dev/kgsl-3d0, /dev/dri/renderD128)"
  fi

  # --- Storage ----------------------------------------------------------
  local data_free; data_free="$(df -h /data 2>/dev/null | awk 'NR==2{print $4}')"
  nt_info "Storage /data free: ${data_free:-unknown}"

  # --- Summary ----------------------------------------------------------
  echo ""
  if [ $rc -eq 0 ]; then
    nt_ok "All checks passed. Ready to start."
  else
    nt_warn "$((${#missing[@]})) item(s) missing. Run 'nativeternux install --yes' to fix."
  fi

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    local missing_json; missing_json="$(nt_json_array "${missing[@]+"${missing[@]}"}")"
    nt_json_object \
      "check" "$([ $rc -eq 0 ] && echo 'pass' || echo 'fail')" \
      "missing_count" "${#missing[@]}" \
      "missing" "$missing_json"
  fi

  return $rc
}

nt_cmd_doctor() {
  nt_cmd_check
  local check_rc=$?
  echo ""
  nt_step "Renderer & Vulkan info..."
  local renderer; renderer="$(_nt_detect_renderer)"
  nt_info "Renderer: $renderer"
  echo ""
  nt_info "Vulkan summary (first 10 lines):"
  _nt_detect_vulkan | head -10
  echo ""
  nt_info "Session status:"
  nt_cmd_status
  return $check_rc
}
