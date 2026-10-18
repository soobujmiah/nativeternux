# Native SSH diagnostics and preview-first control of the fixed Ternuxx Runit unit.

nt_cmd_ssh() {
  local action="${1:-}"; [ $# -gt 0 ] && shift
  case "$action" in
    inspect|start|stop)
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      local format_args=()
      [ "$NATIVERNUX_JSON" = "1" ] && format_args+=(--json)
      local operation="ssh.inspect"
      [ "$action" != "inspect" ] && operation="ssh.service.$action"
      python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" "${format_args[@]}" "$@"
      ;;
    *)
      nt_fail "Supported SSH operations: inspect, start, stop."
      return 2
      ;;
  esac
}
