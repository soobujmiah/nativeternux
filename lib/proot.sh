#!/data/data/com.termux/files/usr/bin/bash
# Read-only inventory of native Termux PRoot distributions.

_nt_proot_call() {
  local args=(--operation proot.status)
  [ "$TERNUXX_JSON" = "1" ] && args+=(--json)
  python3 "$_TN_LIB_DIR/management_service.py" "${args[@]}"
}

_nt_proot_gui() {
  local script="$_TN_LIB_DIR/../scripts/proot-gui0.sh"
  [ -x "$script" ] || { nt_fail "Ternuxx PRoot GUI script is unavailable: $script"; return 1; }
  "$script" "$@"
}

nt_cmd_pgui() {
  if [ "$#" -eq 0 ]; then
    set -- start
  elif [ "$1" = --mode ]; then
    set -- start "$@"
  fi
  _nt_proot_gui "$@"
}

_nt_proot_verify() {
  local distro="$1" guest_user="$2" user_source="$3" display="$4" backend="$5"
  local args=(--operation proot.guest.verify --distro "$distro" --display "$display" --backend "$backend")
  if [ "$user_source" = "rootfs" ]; then
    args+=(--guest-user-source rootfs)
  else
    args+=(--guest-user "$guest_user")
  fi
  [ "$TERNUXX_JSON" = "1" ] && args+=(--json)
  python3 "$_TN_LIB_DIR/management_service.py" "${args[@]}"
}

nt_cmd_proot() {
  local subcommand="${1:-status}"
  [ $# -eq 0 ] || shift
  case "$subcommand" in
    status|inspect)
      [ $# -eq 0 ] || { nt_fail "Use proot status; it only lists installed guests."; return 2; }
      _nt_proot_call
      ;;
    verify)
      local distro="" guest_user="" user_source="" display="" backend="" option value
      while [ "$#" -gt 0 ]; do
        option="$1"; shift
        case "$option" in
          --distro|--guest-user|--guest-user-from|--display|--backend)
            [ "$#" -gt 0 ] || { nt_fail "$option requires a value."; return 2; }
            value="$1"; shift
            case "$option" in
              --distro) distro="$value" ;;
              --guest-user) guest_user="$value" ;;
              --guest-user-from) user_source="$value" ;;
              --display) display="$value" ;;
              --backend) backend="$value" ;;
            esac
            ;;
          --help|-h) nt_help proot; return 0 ;;
          *) nt_fail "Unknown PRoot verify option: $option"; return 2 ;;
        esac
      done
      [ -n "$distro" ] && [ -n "$display" ] && [ -n "$backend" ] || {
        nt_fail "Use proot verify --distro debian --guest-user USER|--guest-user-from rootfs --display :N --backend zink|virgl."
        return 2
      }
      if { [ -n "$guest_user" ] && [ -n "$user_source" ]; } ||
         { [ -z "$guest_user" ] && [ "$user_source" != "rootfs" ]; }; then
        nt_fail "Select exactly one guest-user source: --guest-user USER or --guest-user-from rootfs."
        return 2
      fi
      [ -z "$user_source" ] || [ "$user_source" = "rootfs" ] || {
        nt_fail "Unsupported guest-user source."; return 2;
      }
      _nt_proot_verify "$distro" "$guest_user" "$user_source" "$display" "$backend"
      ;;
    db) _nt_use launch; nt_cmd_db "$@" ;;
    gui)   _nt_proot_gui "$@" ;;
    setup)
      local action="${1:-status}" user="" plan_id="" confirmed=0 option
      [ $# -eq 0 ] || shift
      case "$action" in
        status|adopt-preview|adopt) ;;
        *) nt_fail "Use tx proot setup {status|adopt-preview|adopt}."; return 2 ;;
      esac
      while [ "$#" -gt 0 ]; do
        option="$1"; shift
        case "$option" in
          --user) [ "$#" -gt 0 ] || { nt_fail "--user needs a value."; return 2; }; user="$1"; shift ;;
          --plan-id) [ "$#" -gt 0 ] || { nt_fail "--plan-id needs a value."; return 2; }; plan_id="$1"; shift ;;
          --yes) confirmed=1 ;;
          --help|-h) nt_help proot; return 0 ;;
          *) nt_fail "Unknown PRoot setup option: $option"; return 2 ;;
        esac
      done
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      local repo_root="${_TN_LIB_DIR%/lib}"
      local setup_args=("$action" --repo-root "$repo_root" --json)
      case "$action" in
        status) [ -z "$user" ] && [ -z "$plan_id" ] && [ "$confirmed" -eq 0 ] || {
          nt_fail "Usage: tx proot setup status"; return 2;
        } ;;
        adopt-preview) [ -n "$user" ] && [ -z "$plan_id" ] && [ "$confirmed" -eq 0 ] || {
          nt_fail "Usage: tx proot setup adopt-preview --user NAME"; return 2;
        }; setup_args+=(--user "$user") ;;
        adopt) [ -n "$user" ] && [ -n "$plan_id" ] && [ "$confirmed" -eq 1 ] || {
          nt_fail "Apply requires --user NAME --yes --plan-id ID from an adoption preview."; return 2;
        }; setup_args+=(--user "$user" --yes --plan-id "$plan_id") ;;
      esac
      python3 "$_TN_LIB_DIR/proot_setup.py" "${setup_args[@]}"
      ;;
    *) nt_fail "Use proot status|inspect|verify|db|gui|setup; use tx pgui for the full Debian desktop."; return 2 ;;
  esac
}
