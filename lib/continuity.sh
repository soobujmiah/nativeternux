# Native-only CLI wrapper for private reboot-continuity checkpoints.

nt_cmd_checkpoint() {
  nt_require_termux || return 1
  local action="${1:-}"
  if [ "$#" -gt 0 ]; then shift; fi
  case "$action" in
    prepare|verify) ;;
    *) nt_fail "Usage: ternuxx checkpoint {prepare|verify} [options]"; return 2 ;;
  esac
  local tool
  for tool in python3; do
    nt_require_command "$tool" || return 1
  done
  local format_args=()
  [ "$TERNUXX_JSON" = "1" ] && format_args+=(--json)
  python3 "$_TN_LIB_DIR/management_service.py" \
    --operation "continuity.$action" \
    "${format_args[@]}" "$@"
}
