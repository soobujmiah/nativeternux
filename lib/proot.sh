#!/data/data/com.termux/files/usr/bin/bash
# Read-only inventory of native Termux PRoot distributions.

_nt_proot_call() {
  local args=(--operation proot.status)
  [ "$TERNUXX_JSON" = "1" ] && args+=(--json)
  python3 "$_TN_LIB_DIR/management_service.py" "${args[@]}"
}

_nt_proot_verify() {
  local distro="$1" guest_user="$2" user_source="$3" display="$4" backend="$5"
  local args=(--operation proot.guest.verify --distro "$distro" --display "$display" --backend "$backend")
  if [ "$user_source" = "ternux-state" ]; then
    args+=(--guest-user-source ternux-state)
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
        nt_fail "Use proot verify --distro debian --guest-user USER|--guest-user-from ternux-state --display :N --backend zink|virgl."
        return 2
      }
      if { [ -n "$guest_user" ] && [ -n "$user_source" ]; } ||
         { [ -z "$guest_user" ] && [ "$user_source" != "ternux-state" ]; }; then
        nt_fail "Select exactly one guest-user source: --guest-user USER or --guest-user-from ternux-state."
        return 2
      fi
      [ -z "$user_source" ] || [ "$user_source" = "ternux-state" ] || {
        nt_fail "Unsupported guest-user source."; return 2;
      }
      _nt_proot_verify "$distro" "$guest_user" "$user_source" "$display" "$backend"
      ;;
    *) nt_fail "Use proot status|inspect|verify."; return 2 ;;
  esac
}
