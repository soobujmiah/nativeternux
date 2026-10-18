#!/data/data/com.termux/files/usr/bin/bash

nt_cmd_management() {
  local section="${1:-}"
  [ "$#" -gt 0 ] && shift
  case "$section" in
    app)
      local action="${1:-}"
      [ "$#" -gt 0 ] && shift
      case "$action" in
        launch)
          [ "$#" -eq 1 ] || { nt_fail "Usage: ternuxx management app launch APP_ID"; return 2; }
          nt_require_termux || return 1
          nt_require_command python3 || return 1
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.app.launch --app-id "$1" --json
          ;;
        --help|-h|"") nt_help management ;;
        *) nt_fail "Unknown management app action: $action"; return 2 ;;
      esac
      ;;
    catalog)
      [ "$#" -eq 1 ] && [ "$1" = "list" ] || { nt_fail "Usage: ternuxx management catalog list"; return 2; }
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      python3 "$_TN_LIB_DIR/management_service.py" --operation management.catalog --json
      ;;
    doctor)
      local graphics_flag=""
      [ "$#" -le 1 ] || { nt_fail "Usage: ternuxx management doctor [--graphics]"; return 2; }
      [ "${1:-}" != "--graphics" ] || graphics_flag="--graphics"
      [ -z "${1:-}" ] || [ -n "$graphics_flag" ] || { nt_fail "Usage: ternuxx management doctor [--graphics]"; return 2; }
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      python3 "$_TN_LIB_DIR/management_service.py" --operation doctor.report $graphics_flag --json
      ;;
    shortcuts)
      local action="${1:-}"
      [ "$#" -gt 0 ] && shift
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      case "$action" in
        list)
          [ "$#" -eq 0 ] || { nt_fail "Usage: ternuxx management shortcuts list"; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.shortcuts.list --json
          ;;
        plan)
          [ "$#" -eq 2 ] || { nt_fail "Usage: ternuxx management shortcuts plan {add|remove} APP_ID"; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.shortcuts.preview \
            --shortcut-action "$1" --app-id "$2" --json
          ;;
        apply)
          [ "$#" -eq 5 ] && [ "$3" = "--plan-id" ] && [ "$5" = "--yes" ] || {
            nt_fail "Usage: ternuxx management shortcuts apply {add|remove} APP_ID --plan-id ID --yes"; return 2;
          }
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.shortcuts.apply \
            --shortcut-action "$1" --app-id "$2" --plan-id "$4" --yes --json
          ;;
        --help|-h|"") nt_help management ;;
        *) nt_fail "Unknown shortcuts action: $action"; return 2 ;;
      esac
      ;;
    http)
      local action="${1:-}"
      [ "$#" -gt 0 ] && shift
      case "$action" in
        serve)
          local port=8765
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --port)
                [ "$#" -ge 2 ] || { nt_fail "--port requires a value."; return 2; }
                port="$2"; shift 2 ;;
              --help|-h) nt_help management; return 0 ;;
              *) nt_fail "Unknown management HTTP option: $1"; return 2 ;;
            esac
          done
          nt_require_termux || return 1
          nt_require_command python3 || return 1
          python3 "$_TN_LIB_DIR/management_http_runtime.py" --port "$port"
          ;;
        --help|-h|"") nt_help management ;;
        *) nt_fail "Use 'ternuxx management catalog list', 'ternuxx management doctor', 'ternuxx management shortcuts', or 'ternuxx management http serve'."; return 2 ;;
      esac
      ;;
    --help|-h|"") nt_help management ;;
    *) nt_fail "Use 'ternuxx management catalog list', 'ternuxx management doctor', 'ternuxx management shortcuts', or 'ternuxx management http serve'."; return 2 ;;
  esac
}
