# Native SSH diagnostics and preview-first control of the fixed Ternuxx Runit unit.

nt_cmd_ssh() {
  local action="${1:-}"; [ $# -gt 0 ] && shift
  case "$action" in
    inspect|keys-list|rollback-list|rollback-preview|rollback-apply|enroll-preview|enroll|revoke-preview|revoke|client-key-preview|client-key-create|autostart-status|autostart-preview|autostart-apply|start|stop|restart|deploy|deploy-rollback-preview|deploy-rollback)
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      local format_args=()
      [ "$TERNUXX_JSON" = "1" ] && format_args+=(--json)
      local operation="ssh.inspect"
      [ "$action" != "inspect" ] && operation="ssh.service.$action"
      [ "$action" = "keys-list" ] && operation="ssh.keys.list"
      [ "$action" = "rollback-list" ] && operation="ssh.keys.rollback.list"
      [ "$action" = "rollback-preview" ] && operation="ssh.keys.rollback.preview"
      [ "$action" = "rollback-apply" ] && operation="ssh.keys.rollback.apply"
      [ "$action" = "enroll-preview" ] && operation="ssh.keys.add.preview"
      [ "$action" = "enroll" ] && operation="ssh.keys.add.apply"
      [ "$action" = "revoke-preview" ] && operation="ssh.keys.remove.preview"
      [ "$action" = "revoke" ] && operation="ssh.keys.remove.apply"
      [ "$action" = "client-key-preview" ] && operation="ssh.client-key.create.preview"
      [ "$action" = "client-key-create" ] && operation="ssh.client-key.create.apply"
      [ "$action" = "autostart-status" ] && operation="ssh.service.autostart.status"
      [ "$action" = "autostart-preview" ] && operation="ssh.service.autostart.preview"
      [ "$action" = "autostart-apply" ] && operation="ssh.service.autostart.apply"
      [ "$action" = "deploy-rollback-preview" ] && operation="ssh.service.deploy.rollback.preview"
      [ "$action" = "deploy-rollback" ] && operation="ssh.service.deploy.rollback.apply"
      if [ "$action" = "rollback-preview" ]; then
        [ "$#" -eq 1 ] || { nt_fail "Usage: tx ssh rollback-preview ID"; return 2; }
        python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --operation-id "$1" "${format_args[@]}"
      elif [ "$action" = "rollback-apply" ]; then
        [ "$#" -eq 4 ] && [ "$2" = "--yes" ] && [ "$3" = "--plan-id" ] || {
          nt_fail "Usage: tx ssh rollback-apply ID --yes --plan-id PLAN_ID"; return 2;
        }
        python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --operation-id "$1" --yes --plan-id "$4" "${format_args[@]}"
      else
        python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" "${format_args[@]}" "$@"
      fi
      ;;
    *)
      nt_fail "Supported SSH operations: inspect, keys-list, rollback-list, rollback-preview, rollback-apply, enroll-preview, enroll, revoke-preview, revoke, client-key-preview, client-key-create, autostart-status, autostart-preview, autostart-apply, start, stop, restart, deploy, deploy-rollback-preview, deploy-rollback. Rollback restore requires the listed rollback ID, exact preview, and confirmation. Autostart preference accepts --autostart-enabled or --autostart-disabled; preview before --yes --plan-id."
      return 2
      ;;
  esac
}
