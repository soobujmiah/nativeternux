#!/data/data/com.termux/files/usr/bin/bash
# Local recovery commands use only the typed management-service allowlist.

_nt_recovery_call() {
  local operation="$1"; shift
  local args=("$@")
  [ "$NATIVERNUX_JSON" = "1" ] && args+=(--json)
  python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" "${args[@]}"
}

nt_cmd_backup() {
  local subcommand="${1:-}"; [ $# -gt 0 ] && shift
  case "$subcommand" in
    create)
      local name="" plan_id="" confirmed=0 arg
      while [ $# -gt 0 ]; do
        arg="$1"; shift
        case "$arg" in
          --name) [ $# -gt 0 ] || { nt_fail "--name requires a value."; return 2; }; name="$1"; shift ;;
          --plan-id) [ $# -gt 0 ] || { nt_fail "--plan-id requires a value."; return 2; }; plan_id="$1"; shift ;;
          --yes) confirmed=1 ;;
          --preview) confirmed=0 ;;
          *) nt_fail "Unknown backup option: $arg"; return 2 ;;
        esac
      done
      [ -n "$name" ] || { nt_fail "Use backup create --name NAME to preview a backup."; return 2; }
      local command=(--name "$name")
      if [ "$confirmed" = "1" ]; then
        [ -n "$plan_id" ] || { nt_fail "Backup create requires --plan-id from the exact preview."; return 2; }
        command+=(--yes --plan-id "$plan_id")
      else
        [ -z "$plan_id" ] || { nt_fail "--plan-id requires explicit --yes."; return 2; }
      fi
      _nt_recovery_call backup.create "${command[@]}"
      ;;
    list)
      [ $# -eq 0 ] || { nt_fail "backup list takes no arguments."; return 2; }
      _nt_recovery_call backup.list
      ;;
    inspect)
      [ $# -eq 1 ] || { nt_fail "Use backup inspect BACKUP_ID."; return 2; }
      _nt_recovery_call backup.inspect --backup-id "$1"
      ;;
    *) nt_fail "Use backup create|list|inspect."; return 2 ;;
  esac
}

nt_cmd_restore() {
  local backup_id="" confirmed=0 plan_id="" arg
  if [ "${1:-}" = "--preview" ]; then
    shift
    [ $# -eq 1 ] || { nt_fail "Use restore --preview BACKUP_ID."; return 2; }
    _nt_recovery_call restore.preview --backup-id "$1"
    return $?
  fi
  [ $# -gt 0 ] || { nt_fail "Use restore --preview BACKUP_ID before restoring."; return 2; }
  backup_id="$1"; shift
  while [ $# -gt 0 ]; do
    arg="$1"; shift
    case "$arg" in
      --yes) confirmed=1 ;;
      --plan-id) [ $# -gt 0 ] || { nt_fail "--plan-id requires a value."; return 2; }; plan_id="$1"; shift ;;
      *) nt_fail "Unknown restore option: $arg"; return 2 ;;
    esac
  done
  if [ "$confirmed" = "1" ]; then
    [ -n "$plan_id" ] || { nt_fail "Restore requires --plan-id from the exact preview."; return 2; }
    _nt_recovery_call restore.apply --backup-id "$backup_id" --yes --plan-id "$plan_id"
  else
    [ -z "$plan_id" ] || { nt_fail "--plan-id requires explicit --yes."; return 2; }
    _nt_recovery_call restore.preview --backup-id "$backup_id"
  fi
}

nt_cmd_recovery() {
  local subcommand=""
  if [ "$#" -gt 0 ]; then subcommand="$1"; shift; fi
  case "$subcommand" in
    status)
      [ "$#" -eq 0 ] || { nt_fail "recovery status takes no arguments."; return 2; }
      _nt_recovery_call recovery.status
      ;;
    inspect)
      [ "$#" -eq 1 ] || { nt_fail "Use recovery inspect OPERATION_ID."; return 2; }
      _nt_recovery_call recovery.inspect --operation-id "$1"
      ;;
    resolve)
      local operation_id="" confirmed=0 plan_id="" arg
      [ "$#" -gt 0 ] || { nt_fail "Use recovery resolve OPERATION_ID to preview a supported desktop, service, or boot-profile journal reconciliation."; return 2; }
      operation_id="$1"; shift
      while [ "$#" -gt 0 ]; do
        arg="$1"; shift
        case "$arg" in
          --yes) confirmed=1 ;;
          --plan-id) [ "$#" -gt 0 ] || { nt_fail "--plan-id requires a value."; return 2; }; plan_id="$1"; shift ;;
          --preview) confirmed=0 ;;
          *) nt_fail "Unknown recovery resolve option: $arg"; return 2 ;;
        esac
      done
      if [ "$confirmed" = "1" ]; then
        [ -n "$plan_id" ] || { nt_fail "Recovery resolve requires --plan-id from the exact preview."; return 2; }
        _nt_recovery_call recovery.resolve --operation-id "$operation_id" --yes --plan-id "$plan_id"
      else
        [ -z "$plan_id" ] || { nt_fail "--plan-id requires explicit --yes."; return 2; }
        _nt_recovery_call recovery.resolve --operation-id "$operation_id"
      fi
      ;;
    rollback)
      local operation_id="" confirmed=0 plan_id="" arg
      [ "$#" -gt 0 ] || { nt_fail "Use recovery rollback OPERATION_ID to preview."; return 2; }
      operation_id="$1"; shift
      while [ "$#" -gt 0 ]; do
        arg="$1"; shift
        case "$arg" in
          --yes) confirmed=1 ;;
          --plan-id) [ "$#" -gt 0 ] || { nt_fail "--plan-id requires a value."; return 2; }; plan_id="$1"; shift ;;
          --preview) confirmed=0 ;;
          *) nt_fail "Unknown recovery rollback option: $arg"; return 2 ;;
        esac
      done
      if [ "$confirmed" = "1" ]; then
        [ -n "$plan_id" ] || { nt_fail "Recovery rollback requires --plan-id from the exact preview."; return 2; }
        _nt_recovery_call recovery.rollback.apply --operation-id "$operation_id" --yes --plan-id "$plan_id"
      else
        [ -z "$plan_id" ] || { nt_fail "--plan-id requires explicit --yes."; return 2; }
        _nt_recovery_call recovery.rollback.preview --operation-id "$operation_id"
      fi
      ;;
    *) nt_fail "Use recovery status|inspect|resolve|rollback."; return 2 ;;
  esac
}
