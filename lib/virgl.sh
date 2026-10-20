#!/data/data/com.termux/files/usr/bin/bash

nt_cmd_virgl() {
  local action="${1:-status}" display=":1" flag
  [ $# -eq 0 ] || shift
  while [ $# -gt 0 ]; do
    flag="$1"; shift
    case "$flag" in
      --display)
        [ $# -gt 0 ] || { nt_fail "--display requires :N"; return 2; }
        display="$1"; shift ;;
      --help|-h) nt_help virgl; return 0 ;;
      *) nt_fail "Unknown VirGL option: $flag"; return 2 ;;
    esac
  done
  case "$action" in
    --help|-h) nt_help virgl; return 0 ;;
    status|start|stop) ;;
    *) nt_fail "Use tx virgl [status|start|stop] [--display :N]."; return 2 ;;
  esac
  [ "${PREFIX:-}" = "/data/data/com.termux/files/usr" ] && [ -n "${TERMUX_VERSION:-}" ] || {
    nt_fail "VirGL service management requires the Native Termux shell, not Debian PRoot.";
    return 1
  }
  nt_require_command python3 || return 1
  python3 "$_TN_LIB_DIR/virgl_lifecycle.py" "$action" --display "$display"
}
