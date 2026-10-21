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
  "$BASH" "$script" "$@"
}

nt_cmd_pgui() {
  if [ "$#" -eq 0 ]; then
    set -- start
  elif [ "$1" = --mode ]; then
    set -- start "$@"
  fi
  _nt_proot_gui "$@"
}


# Compatibility entry used by existing Native XFCE menu items. These are
# fixed desktop commands mapped to the shared, provider-aware app launcher.
nt_cmd_app() {
  [ "$#" -ge 2 ] && [ "$1" = -- ] || {
    nt_fail "Usage: tx app -- ALLOWLISTED_DEBIAN_APP [fixed options]"
    return 2
  }
  shift
  local app_id="" program="$1"
  case "$program" in
    thunar)
      if [ "$#" -eq 1 ]; then app_id=files
      elif [ "$#" -eq 2 ] && [ "$2" = --bulk-rename ]; then app_id=thunar-bulk-rename
      fi
      ;;
    xfce4-terminal)
      if [ "$#" -eq 1 ]; then app_id=terminal
      elif [ "$#" -eq 2 ] && [ "$2" = --preferences ]; then app_id=xfce4-terminal-settings
      fi
      ;;
    firefox-esr|/usr/lib/firefox-esr/firefox-esr) [ "$#" -eq 1 ] && app_id=firefox ;;
    /usr/bin/vlc)
      if [ "$#" -eq 1 ] || { [ "$#" -eq 2 ] && [ "$2" = --started-from-file ]; }; then app_id=vlc; fi
      ;;
    blender|pavucontrol|system-config-printer|thunar-settings|thunar-volman-settings|xarchiver|xfce4-appfinder)
      [ "$#" -eq 1 ] && app_id="$program" ;;
    --help|-h)
      printf '%s\n' "Usage: tx app -- ALLOWLISTED_DEBIAN_APP [fixed options]"         "Compatibility route for existing Native XFCE PRoot menu entries."
      return 0
      ;;
  esac
  [ -n "$app_id" ] || {
    nt_fail "Unsupported or malformed Debian menu app; no guest command was run."
    return 2
  }
  nt_require_termux || return 1
  nt_require_command python3 || return 1
  local -a launch_args=(--operation proot.app.launch --app-id "$app_id")
  [ "$TERNUXX_JSON" = "1" ] && launch_args+=(--json)
  python3 "$_TN_LIB_DIR/management_service.py" "${launch_args[@]}"
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
    legacy-cli)
      local scope="guest" action="" plan_id="" backup_id="" option
      if [ "${1:-}" = "host" ]; then scope="host"; shift; fi
      action="${1:-}"
      [ "$#" -gt 0 ] || { nt_fail "Use tx proot legacy-cli [host] {preview|remove|rollback} [plan options]."; return 2; }
      shift
      case "$action" in preview|remove|rollback) ;; *) nt_fail "Use tx proot legacy-cli [host] {preview|remove|rollback}."; return 2 ;; esac
      while [ "$#" -gt 0 ]; do
        option="$1"; shift
        case "$option" in
          --plan-id) [ "$#" -gt 0 ] || { nt_fail "--plan-id needs a value."; return 2; }; plan_id="$1"; shift ;;
          --backup-id) [ "$#" -gt 0 ] || { nt_fail "--backup-id needs a value."; return 2; }; backup_id="$1"; shift ;;
          *) nt_fail "Unknown legacy CLI option: $option"; return 2 ;;
        esac
      done
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      local state_dir="${TERNUXX_STATE_DIR:-$HOME/.local/share/ternuxx}"
      local tool_action="$action" tool="$_TN_LIB_DIR/../tools/retire_legacy_guest_cli.py"
      local -a retirement_args=()
      [ "$action" = "remove" ] && tool_action="apply"
      if [ "$scope" = "host" ]; then
        tool="$_TN_LIB_DIR/../tools/retire_legacy_host_cli.py"
        retirement_args=("$tool_action" --prefix "$PREFIX" --state-dir "$state_dir" --json)
      else
        local rootfs="$PREFIX/var/lib/proot-distro/containers/debian/rootfs"
        retirement_args=("$tool_action" --rootfs "$rootfs" --state-dir "$state_dir" --json)
      fi
      case "$action" in
        preview) [ -z "$plan_id" ] && [ -z "$backup_id" ] || { nt_fail "Usage: tx proot legacy-cli [host] preview"; return 2; } ;;
        remove) [ -n "$plan_id" ] && [ -z "$backup_id" ] || { nt_fail "Remove requires --plan-id from the exact preview."; return 2; }; retirement_args+=(--plan-id "$plan_id") ;;
        rollback) [ -n "$backup_id" ] && [ -z "$plan_id" ] || { nt_fail "Rollback requires --backup-id from the retirement result."; return 2; }; retirement_args+=(--backup-id "$backup_id") ;;
      esac
      python3 "$tool" "${retirement_args[@]}"
      ;;
    db) _nt_use launch; nt_cmd_db "$@" ;;
    gui)   _nt_proot_gui "$@" ;;
    setup)
      local action="${1:-status}" user="" plan_id="" confirmed=0 option
      [ $# -eq 0 ] || shift
      case "$action" in
        status|adopt-preview|adopt|fresh-preview|fresh-install) ;;
        *) nt_fail "Use tx proot setup {status|adopt-preview|adopt|fresh-preview|fresh-install}."; return 2 ;;
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
        adopt|fresh-install) [ -n "$user" ] && [ -n "$plan_id" ] && [ "$confirmed" -eq 1 ] || {
          nt_fail "Apply requires --user NAME --yes --plan-id ID from the matching setup preview."; return 2;
        }; setup_args+=(--user "$user" --yes --plan-id "$plan_id") ;;
        fresh-preview) [ -n "$user" ] && [ -z "$plan_id" ] && [ "$confirmed" -eq 0 ] || {
          nt_fail "Usage: tx proot setup fresh-preview --user NAME"; return 2;
        }; setup_args+=(--user "$user") ;;
      esac
      python3 "$_TN_LIB_DIR/proot_setup.py" "${setup_args[@]}"
      ;;
    *) nt_fail "Use proot status|inspect|verify|legacy-cli [host]|db|gui|setup; use tx pgui for the full Debian desktop."; return 2 ;;
  esac
}
