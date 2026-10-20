#!/data/data/com.termux/files/usr/bin/bash

nt_audio_call() {
  local action="$1"
  nt_require_termux || return 1
  nt_require_command python3 || return 1
  python3 "$_TN_LIB_DIR/pulse_lifecycle.py" "$action"
}

nt_audio_ensure() {
  local result
  result="$(nt_audio_call ensure 2>&1)" || {
    nt_warn "Native PulseAudio is unavailable; GUI/PRoot CLI will continue without audio. $result"
    return 1
  }
  nt_info "Native PulseAudio is ready for PRoot clients."
}

nt_cmd_audio() {
  local action="${1:-status}"
  [ $# -eq 0 ] || shift
  case "$action" in
    --help|-h) nt_help audio; return 0 ;;
    status|start|stop|restart) [ $# -eq 0 ] || { nt_fail "Usage: tx audio [status|start|stop|restart]"; return 2; } ;;
    *) nt_fail "Use tx audio [status|start|stop|restart]."; return 2 ;;
  esac
  nt_audio_call "$action"
}
