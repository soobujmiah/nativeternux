# =============================================================================
#  nativeternux — desktop lifecycle (start / stop / restart / status)
#
#  NOTE: This is a scaffold for milestone 1. The start function currently
#  reports readiness but does NOT launch a real session until packages
#  are installed and validated. See docs/ROADMAP.md for milestone gates.
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

# --- Native start -------------------------------------------------------
nt_cmd_start() {
  nt_step "Starting NativeTernux desktop..."

  # 1. Check required packages
  local missing=()
  for pkg in xfce4-session xfce4-panel xfwm4; do
    if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
      missing+=("$pkg")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    nt_fail "Required packages not installed: ${missing[*]}"
    nt_info "Run 'nativeternux install --yes' to install them."
    [ "$NATIVERNUX_JSON" = "1" ] && \
      nt_json_object "start" "error" "reason" "packages_missing" "missing" "$(nt_json_array "${missing[@]}")"
    return 1
  fi

  # 2. Check Termux:X11 binary
  if [ ! -f "/data/data/com.termux/files/usr/bin/termux-x11" ]; then
    nt_fail "Termux:X11 app not found. Install from F-Droid or GitHub."
    return 1
  fi

  # 3. Find free display
  local display_num; display_num="$(nt_find_free_display)"
  if [ "$display_num" = "error" ]; then
    nt_fail "Could not find a free X11 display number."
    return 1
  fi
  local DISPLAY_NUM=":$display_num"
  nt_info "Using display $DISPLAY_NUM"

  # 4. Check dbus
  if ! command -v dbus-launch >/dev/null 2>&1; then
    nt_fail "dbus-launch not found. Run 'nativeternux install --yes'."
    return 1
  fi

  # 5. Check pulseaudio
  if ! command -v pulseaudio >/dev/null 2>&1; then
    nt_fail "pulseaudio not found. Run 'nativeternux install --yes'."
    return 1
  fi

  # 6. Verify no conflicting session
  if [ -e "/data/data/com.termux/files/usr/tmp/.X11-unix/X$display_num" ]; then
    nt_warn "Socket $DISPLAY_NUM already exists. Stale socket?"
    # Don't remove — could be another session. Report and exit.
    nt_fail "Remove the stale socket manually, or use a different display number."
    return 1
  fi

  # 7. (Future) Launch sequence
  #    a. termux-x11 $DISPLAY_NUM -ac &
  #    b. Wait for socket
  #    c. pulseaudio --start ...
  #    d. dbus-launch --exit-with-session xfce4-session
  #
  #    For now: report readiness
  nt_ok "All prerequisites met for display $DISPLAY_NUM"
  nt_info "Ready to launch. Full start sequence will be implemented in milestone 2."
  nt_info "Required packages: xfce4-session, xfce4-panel, xfwm4, thunar, xfce4-terminal"
  nt_info "Found: $(command -v termux-x11), $(command -v dbus-launch), $(command -v pulseaudio)"

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object \
      "start" "ready" \
      "display" "$DISPLAY_NUM" \
      "packages_installed" "$(nt_json_array xfce4-session xfce4-panel xfwm4)" \
      "termux_x11" "$(command -v termux-x11)" \
      "dbus_launch" "$(command -v dbus-launch)" \
      "pulseaudio" "$(command -v pulseaudio)"
  fi

  return 0
}

# --- Stop ----------------------------------------------------------------
nt_cmd_stop() {
  nt_step "Stopping NativeTernux session..."

  local found=0

  # Stop only processes we track (future: read from pids.log)
  # For now: check if termux-x11 is running
  if pgrep -f "termux-x11" >/dev/null 2>&1; then
    nt_warn "termux-x11 process found (manual kill required — milestone 2)"
    found=1
  fi

  if [ $found -eq 0 ]; then
    nt_info "No active session found."
  fi

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object "stop" "ok" "cleaned" "$([ $found -eq 0 ] && echo 'yes' || echo 'no')"
  fi
  return 0
}

# --- Restart -------------------------------------------------------------
nt_cmd_restart() {
  nt_cmd_stop
  sleep 1
  nt_cmd_start
}

# --- Status --------------------------------------------------------------
nt_cmd_status() {
  local x11=0 pa=0 xfce=0
  pgrep -f "termux-x11" >/dev/null 2>&1 && x11=1
  pgrep -x pulseaudio >/dev/null 2>&1 && pa=1
  pgrep -f "xfce4-session" >/dev/null 2>&1 && xfce=1

  local overall="stopped"
  [ $xfce -eq 1 ] && overall="running"

  if [ "$NATIVERNUX_JSON" = "1" ]; then
    nt_json_object \
      "status" "$overall" \
      "x11_running" "$([ $x11 -eq 1 ] && echo 'yes' || echo 'no')" \
      "pulseaudio" "$([ $pa -eq 1 ] && echo 'running' || echo 'stopped')" \
      "xfce4_session" "$([ $xfce -eq 1 ] && echo 'running' || echo 'stopped')"
  else
    printf '  %-15s %s\n' "Termux:X11:" "$([ $x11 -eq 1 ] && echo 'running' || echo 'stopped')"
    printf '  %-15s %s\n' "PulseAudio:" "$([ $pa -eq 1 ] && echo 'running' || echo 'stopped')"
    printf '  %-15s %s\n' "XFCE4 Session:" "$([ $xfce -eq 1 ] && echo 'running' || echo 'stopped')"
    printf '\n  Overall: %s\n' "$overall"
  fi
}
