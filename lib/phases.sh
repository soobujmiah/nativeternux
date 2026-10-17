# =============================================================================
#  nativeternux — installation phases
#
#  MILESTONE 1: Scaffold only. No installation is performed.
#  The install command exists for documentation and future implementation.
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

nt_cmd_install() {
  local yes=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --yes) yes=1; shift ;;
      *) nt_fail "Unknown install option: $1"; return 1 ;;
    esac
  done

  if [ "$yes" != "1" ]; then
    nt_fail "Package installation requires explicit --yes consent."
    nt_info "Run: nativeternux install --yes"
    return 1
  fi

  nt_step "Installing NativeTernux packages..."

  local to_install=()
  local pkgs=("xfce4-session" "xfce4-panel" "xfwm4" "thunar" "xfce4-terminal" "pulseaudio" "dbus-x11")

  for pkg in "${pkgs[@]}"; do
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
      nt_ok "$pkg: already installed"
    else
      to_install+=("$pkg")
    fi
  done

  if [ ${#to_install[@]} -eq 0 ]; then
    nt_ok "All packages already installed."
    return 0
  fi

  nt_info "Will install: ${to_install[*]}"
  nt_info "This will use pkg install. Confirm you want to proceed."

  # TODO milestone 2: actual pkg install
  nt_warn "Package installation not yet implemented (milestone 2)."
  nt_info "Run manually: pkg install xfce4-session xfce4-panel xfwm4 thunar xfce4-terminal pulseaudio dbus-x11"

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object \
      "install" "skipped" \
      "reason" "milestone_not_reached" \
      "packages_needed" "$(nt_json_array "${to_install[@]}")"
  fi
  return 0
}

# --- Stub functions for future phases -----------------------------------
nt_phase_packages() {
  nt_warn "nt_phase_packages: not yet implemented"
  return 1
}

nt_phase_gpu() {
  nt_warn "nt_phase_gpu: not yet implemented"
  return 1
}

nt_phase_launcher() {
  nt_warn "nt_phase_launcher: not yet implemented"
  return 1
}

nt_phase_verify() {
  nt_warn "nt_phase_verify: not yet implemented"
  return 1
}
