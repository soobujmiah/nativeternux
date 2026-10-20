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
          [ "$#" -ge 1 ] || { nt_fail "Usage: tx mng app launch APP_ID [--display :N]"; return 2; }
          local app_id="$1" display=""
          shift
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --display)
                [ "$#" -ge 2 ] || { nt_fail "--display requires an X11 display"; return 2; }
                display="$2"; shift 2 ;;
              *) nt_fail "Unknown app launch option: $1"; return 2 ;;
            esac
          done
          nt_require_termux || return 1
          nt_require_command python3 || return 1
          local -a launch_args=(--operation proot.app.launch --app-id "$app_id")
          [ -z "$display" ] || launch_args+=(--display "$display")
          python3 "$_TN_LIB_DIR/management_service.py" "${launch_args[@]}" --json
          ;;
        --help|-h|"") nt_help management ;;
        *) nt_fail "Unknown management app action: $action"; return 2 ;;
      esac
      ;;
    center)
      local action="${1:-}"
      [ "$#" -eq 0 ] || shift
      case "$action" in
        install)
          [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng center install"; return 2; }
          bash "$_NT_BIN_DIR/../scripts/install-management-center.sh"
          ;;
        ""|open|start)
          [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng center"; return 2; }
          nt_require_termux || return 1
          local app="$PREFIX/bin/tx-management-center"
          [ -x "$app" ] || { nt_fail "GTK management client is not installed; run 'tx mng center install'."; return 1; }
          nt_require_command python3 || return 1
          _nt_use desktop || return 1
          _nt_adopt_live_session_state
          local session_report session_state session_display selected_display
          session_report="$(python3 "$_TN_LIB_DIR/desktop_session_state.py" inspect "$HOME" "$TERNUXX_STATE_DIR" /proc "${TMPDIR:-$PREFIX/tmp}" 2>/dev/null)" || {
            nt_fail "Could not verify the Ternuxx-owned Native desktop session; run 'tx status' before opening the management center."
            return 1
          }
          session_state="$(printf '%s' "$session_report" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("state", "unknown"))')" || session_state=unknown
          session_display="$(printf '%s' "$session_report" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("display", ""))')" || session_display=""
          [ "$session_state" = running ] || {
            nt_fail "The Ternuxx Native desktop is not verified running. Run 'tx start', then retry 'tx gui'."
            return 1
          }
          [ -n "$session_display" ] || { nt_fail "The verified Ternuxx session has no display identity."; return 1; }
          if [ -n "${DISPLAY:-}" ] && [ "$DISPLAY" != "$session_display" ]; then
            nt_fail "DISPLAY=$DISPLAY does not match the verified Ternuxx display $session_display; refusing to attach to another session."
            return 1
          fi
          selected_display="$session_display"
          local probe="$_NT_BIN_DIR/../scripts/native_display_probe.py"
          local display_result
          display_result="$(python3 "$probe" "$selected_display" "${TMPDIR:-$PREFIX/tmp}" 2>&1)" || {
            nt_fail "Cannot open the selected Native Termux display: $display_result"
            return 1
          }
          _nt_use audio || return 1
          nt_audio_ensure || true
          DISPLAY="$selected_display" "$app"
          ;;
        --help|-h) nt_help management ;;
        *) nt_fail "Use 'tx mng center [install]'."; return 2 ;;
      esac
      ;;
    catalog)
      local action="${1:-}"
      [ "$#" -gt 0 ] && shift
      [ "$action" = "list" ] || { nt_fail "Usage: tx mng catalog list [--category ID] [--query TEXT] [--status STATE]"; return 2; }
      local -a catalog_args=()
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --category|--query|--status)
            [ "$#" -ge 2 ] || { nt_fail "$1 requires a value"; return 2; }
            case "$1" in --category) catalog_args+=(--category "$2");; --query) catalog_args+=(--query "$2");; --status) catalog_args+=(--status "$2");; esac
            shift 2 ;;
          *) nt_fail "Unknown catalog option: $1"; return 2 ;;
        esac
      done
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      python3 "$_TN_LIB_DIR/management_service.py" --operation management.catalog "${catalog_args[@]}" --json
      ;;
    proot)
      local area="status" action="list" operation="proot.status" profile="" session_id="" confirmed=0 plan_id="" timeout=300
      [ "$#" -eq 0 ] || area="$1"
      [ "$#" -eq 0 ] || shift
      case "$area" in
        status) [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng proot status"; return 2; } ;;
        profiles)
          [ "$#" -eq 0 ] || action="$1"
          [ "$#" -eq 0 ] || shift
          case "$action" in
            list) [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng proot profiles list"; return 2; }; operation="proot.profiles.list" ;;
            show) [ "$#" -eq 1 ] || { nt_fail "Usage: tx mng proot profiles show PROFILE"; return 2; }; operation="proot.profiles.show"; profile="$1" ;;
            *) nt_fail "Use tx mng proot profiles {list|show}."; return 2 ;;
          esac ;;
        sessions)
          [ "$#" -eq 0 ] || action="$1"
          [ "$#" -eq 0 ] || shift
          case "$action" in
            list) operation="proot.sessions.list"; [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng proot sessions list"; return 2; } ;;
            show|health) [ "$#" -eq 1 ] || { nt_fail "Usage: tx mng proot sessions $action SESSION_ID"; return 2; }; session_id="$1"; operation="proot.sessions.$action" ;;
            *) nt_fail "Use tx mng proot sessions {list|show|health}."; return 2 ;;
          esac ;;
        recover)
          [ "$#" -eq 1 ] || { nt_fail "Usage: tx mng proot recover SESSION_ID"; return 2; }
          operation="proot.recovery.inspect"; session_id="$1" ;;
        reconcile)
          [ "$#" -ge 1 ] || { nt_fail "Usage: tx mng proot reconcile SESSION_ID [--yes --plan-id PLAN]"; return 2; }
          session_id="$1"; shift
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --yes) confirmed=1; shift ;;
              --plan-id) [ "$#" -ge 2 ] || { nt_fail "--plan-id requires a value"; return 2; }; plan_id="$2"; shift 2 ;;
              *) nt_fail "Unknown PRoot reconcile option: $1"; return 2 ;;
            esac
          done
          if [ "$confirmed" -eq 1 ]; then operation="proot.recovery.reconcile"; else operation="proot.recovery.reconcile.preview"; fi ;;
        start)
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --profile) [ "$#" -ge 2 ] || { nt_fail "--profile requires a value"; return 2; }; profile="$2"; shift 2 ;;
              --timeout-seconds) [ "$#" -ge 2 ] || { nt_fail "--timeout-seconds requires a value"; return 2; }; timeout="$2"; shift 2 ;;
              --yes) confirmed=1; shift ;;
              --plan-id) [ "$#" -ge 2 ] || { nt_fail "--plan-id requires a value"; return 2; }; plan_id="$2"; shift 2 ;;
              *) nt_fail "Unknown PRoot start option: $1"; return 2 ;;
            esac
          done
          [ -n "$profile" ] || { nt_fail "Use tx mng proot start --profile PROFILE."; return 2; }
          if [ "$confirmed" -eq 1 ]; then operation="proot.start"; else operation="proot.start.preview"; fi ;;
        stop)
          [ "$#" -ge 1 ] || { nt_fail "Usage: tx mng proot stop SESSION_ID [--yes --plan-id PLAN]"; return 2; }
          session_id="$1"; shift
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --yes) confirmed=1; shift ;;
              --plan-id) [ "$#" -ge 2 ] || { nt_fail "--plan-id requires a value"; return 2; }; plan_id="$2"; shift 2 ;;
              *) nt_fail "Unknown PRoot stop option: $1"; return 2 ;;
            esac
          done
          if [ "$confirmed" -eq 1 ]; then operation="proot.stop"; else operation="proot.stop.preview"; fi ;;
        *) nt_fail "Use tx mng proot {status|profiles|sessions|recover|reconcile|start|stop}."; return 2 ;;
      esac
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      case "$operation" in
        proot.profiles.show|proot.start.preview)
          python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --profile "$profile" --json ;;
        proot.sessions.show|proot.sessions.health|proot.stop.preview|proot.recovery.inspect|proot.recovery.reconcile.preview)
          python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --operation-id "$session_id" --json ;;
        proot.start)
          [ -n "$plan_id" ] || { nt_fail "A preview --plan-id is required with --yes."; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --profile "$profile" --yes --plan-id "$plan_id" --timeout-seconds "$timeout" --json ;;
        proot.recovery.reconcile)
          [ -n "$plan_id" ] || { nt_fail "A preview --plan-id is required with --yes."; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --operation-id "$session_id" --yes --plan-id "$plan_id" --json ;;
        proot.stop)
          [ -n "$plan_id" ] || { nt_fail "A preview --plan-id is required with --yes."; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --operation-id "$session_id" --yes --plan-id "$plan_id" --json ;;
        *) python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --json ;;
      esac
      ;;
    timezone)
      local action="${1:-status}"
      [ "$#" -gt 0 ] && shift
      local operation="timezone.$action"
      case "$action" in
        status|list) [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng timezone $action"; return 2; } ;;
        set)
          [ "$#" -eq 1 ] || { nt_fail "Usage: tx mng timezone set IANA_NAME"; return 2; }
          local timezone_name="$1"
          ;;
        --help|-h) nt_help management; return 0 ;;
        *) nt_fail "Use tx mng timezone {status|list|set IANA_NAME}."; return 2 ;;
      esac
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      if [ "$action" = "set" ]; then
        python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --timezone "$timezone_name" --json
      else
        python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" --json
      fi
      ;;
    cron)
      local area="${1:-status}"
      [ "$#" -eq 0 ] || shift
      local operation="cron.status"
      local -a cron_args=()
      case "$area" in
        start)
          operation="cron.scheduler.start"
          local start_confirmed=0
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --yes) start_confirmed=1; cron_args+=(--yes); shift ;;
              --poll-seconds) [ "$#" -ge 2 ] || { nt_fail "--poll-seconds requires a value"; return 2; }; cron_args+=(--poll-seconds "$2"); shift 2 ;;
              *) nt_fail "Unknown scheduler start option: $1"; return 2 ;;
            esac
          done
          [ "$start_confirmed" -eq 1 ] || { nt_fail "Starting Cron may run enabled jobs; confirm with --yes."; return 2; } ;;
        stop)
          [ "$#" -eq 1 ] && [ "$1" = "--yes" ] || { nt_fail "Usage: tx mng cron stop --yes"; return 2; }
          operation="cron.scheduler.stop"; cron_args+=(--yes) ;;
        executions)
          local action="${1:-list}"
          [ "$#" -eq 0 ] || shift
          case "$action" in
            list)
              operation="cron.executions.list"
              while [ "$#" -gt 0 ]; do
                case "$1" in
                  --job-id) [ "$#" -ge 2 ] || { nt_fail "--job-id requires an ID"; return 2; }; cron_args+=(--job-id "$2"); shift 2 ;;
                  --limit) [ "$#" -ge 2 ] || { nt_fail "--limit requires a number"; return 2; }; cron_args+=(--limit "$2"); shift 2 ;;
                  *) nt_fail "Unknown executions list option: $1"; return 2 ;;
                esac
              done ;;
            show)
              [ "$#" -eq 1 ] || { nt_fail "Usage: tx mng cron executions show EXECUTION_ID"; return 2; }
              operation="cron.executions.show"; cron_args+=(--execution-id "$1") ;;
            *) nt_fail "Use tx mng cron executions {list|show}."; return 2 ;;
          esac ;;
        status) [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng cron status"; return 2; } ;;
        jobs)
          local action="${1:-list}"
          [ "$#" -eq 0 ] || shift
          case "$action" in
            list) operation="cron.jobs.list"; [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng cron jobs list"; return 2; } ;;
            validate)
              if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then cron_args+=(--job-id "$1"); shift; fi
              operation="cron.jobs.validate"; cron_args+=("$@");;
            show|next-runs|remove|enable|disable|update)
              [ "$#" -ge 1 ] || { nt_fail "Usage: tx mng cron jobs $action JOB_ID [options]"; return 2; }
              local job_id="$1"; shift
              case "$action" in
                show) operation="cron.jobs.show"; [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng cron jobs show JOB_ID"; return 2; }; cron_args+=(--job-id "$job_id") ;;
                next-runs) operation="cron.jobs.next_runs"; cron_args+=(--job-id "$job_id"); while [ "$#" -gt 0 ]; do case "$1" in --count) [ "$#" -ge 2 ] || { nt_fail "--count requires a number"; return 2; }; cron_args+=(--count "$2"); shift 2;; *) nt_fail "Unknown next-runs option: $1"; return 2;; esac; done ;;
                remove) operation="cron.jobs.remove"; [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng cron jobs remove JOB_ID"; return 2; }; cron_args+=(--job-id "$job_id") ;;
                enable|disable) operation="cron.jobs.update"; [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng cron jobs $action JOB_ID"; return 2; }; cron_args+=(--job-id "$job_id" "$( [ "$action" = enable ] && echo --job-enabled || echo --job-disabled )") ;;
                update) operation="cron.jobs.update"; cron_args+=(--job-id "$job_id" "$@") ;;
              esac ;;
            create) operation="cron.jobs.create"; cron_args+=("$@") ;;
            *) nt_fail "Use tx mng cron jobs {list|show|validate|next-runs|create|update|enable|disable|remove}."; return 2 ;;
          esac ;;
        *) nt_fail "Use tx mng cron {status|start|stop|jobs|executions}."; return 2 ;;
      esac
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" "${cron_args[@]}" --json
      ;;
    boot)
      local boot_area="${1:-cron}"
      [ "$#" -gt 0 ] && shift
      [ "$boot_area" = "cron" ] || { nt_fail "Use tx mng boot cron {status|validate|preview|enable|disable}."; return 2; }
      local action="${1:-status}"
      [ "$#" -gt 0 ] && shift
      local operation="boot.cron.status" boot_action="" confirmed=0 plan_id=""
      case "$action" in
        status|validate) [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng boot cron $action"; return 2; }
          [ "$action" = "validate" ] && operation="boot.cron.validate" ;;
        preview)
          [ "$#" -eq 1 ] && { [ "$1" = "enable" ] || [ "$1" = "disable" ]; } || { nt_fail "Usage: tx mng boot cron preview {enable|disable}"; return 2; }
          operation="boot.cron.preview"; boot_action="$1" ;;
        enable|disable)
          operation="boot.cron.$action"
          while [ "$#" -gt 0 ]; do
            case "$1" in
              --yes) confirmed=1; shift ;;
              --plan-id) [ "$#" -ge 2 ] || { nt_fail "--plan-id requires the exact preview ID"; return 2; }; plan_id="$2"; shift 2 ;;
              *) nt_fail "Unknown boot integration option: $1"; return 2 ;;
            esac
          done
          [ "$confirmed" -eq 1 ] && [ -n "$plan_id" ] || { nt_fail "Preview first, then confirm with --yes --plan-id PLAN_ID."; return 2; } ;;
        *) nt_fail "Use tx mng boot cron {status|validate|preview|enable|disable}."; return 2 ;;
      esac
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      local -a boot_args=(--operation "$operation")
      [ -z "$boot_action" ] || boot_args+=(--boot-action "$boot_action")
      [ "$confirmed" -eq 0 ] || boot_args+=(--yes --plan-id "$plan_id")
      python3 "$_TN_LIB_DIR/management_service.py" "${boot_args[@]}" --json
      ;;
    hermes)
      local action="${1:-}"
      [ "$#" -gt 0 ] && shift
      [ "$action" = "status" ] && [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng hermes status"; return 2; }
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      python3 "$_TN_LIB_DIR/management_service.py" --operation agent.hermes.status --json
      ;;
    doctor)
      local graphics_flag=""
      [ "$#" -le 1 ] || { nt_fail "Usage: tx mng doctor [--graphics]"; return 2; }
      [ "${1:-}" != "--graphics" ] || graphics_flag="--graphics"
      [ -z "${1:-}" ] || [ -n "$graphics_flag" ] || { nt_fail "Usage: tx mng doctor [--graphics]"; return 2; }
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
          [ "$#" -eq 0 ] || { nt_fail "Usage: tx mng shortcuts list"; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.shortcuts.list --json
          ;;
        plan)
          [ "$#" -eq 2 ] || { nt_fail "Usage: tx mng shortcuts plan {add|remove} APP_ID"; return 2; }
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.shortcuts.preview \
            --shortcut-action "$1" --app-id "$2" --json
          ;;
        apply)
          [ "$#" -eq 5 ] && [ "$3" = "--plan-id" ] && [ "$5" = "--yes" ] || {
            nt_fail "Usage: tx mng shortcuts apply {add|remove} APP_ID --plan-id ID --yes"; return 2;
          }
          python3 "$_TN_LIB_DIR/management_service.py" --operation proot.shortcuts.apply \
            --shortcut-action "$1" --app-id "$2" --plan-id "$4" --yes --json
          ;;
        --help|-h|"") nt_help management ;;
        *) nt_fail "Unknown shortcuts action: $action"; return 2 ;;
      esac
      ;;
    web)
      local port=8765 show_secret_fallback=0
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --port) [ "$#" -ge 2 ] || { nt_fail "--port requires a value."; return 2; }; port="$2"; shift 2 ;;
          --show-secret-on-clipboard-failure) show_secret_fallback=1; shift ;;
          --help|-h) nt_help web; return 0 ;;
          *) nt_fail "Unknown Web UI option: $1"; return 2 ;;
        esac
      done
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      local -a web_args=(--port "$port" --web)
      [ "$show_secret_fallback" -eq 0 ] || web_args+=(--show-secret-on-clipboard-failure)
      python3 "$_TN_LIB_DIR/management_http_runtime.py" "${web_args[@]}"
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
        *) nt_fail "Use 'tx mng center', 'tx mng catalog list', 'tx mng doctor', 'tx mng shortcuts', or 'tx mng http serve'."; return 2 ;;
      esac
      ;;
    --help|-h|"") nt_help management ;;
    *) nt_fail "Use 'tx mng center', 'tx mng catalog list', 'tx mng doctor', 'tx mng shortcuts', or 'tx mng http serve'."; return 2 ;;
  esac
}

nt_cmd_web() { nt_cmd_management web "$@"; }
