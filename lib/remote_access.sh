#!/data/data/com.termux/files/usr/bin/bash
# Offline private-transport policy preview; never enables remote access.

nt_cmd_remote() {
  local section="${1:-}"
  [ "$#" -gt 0 ] && shift
  case "$section" in
    access)
      local action="${1:-}"
      [ "$#" -gt 0 ] && shift
      case "$action" in
        preview)
          local policy_stdin=0 arg
          while [ "$#" -gt 0 ]; do
            arg="$1"; shift
            case "$arg" in
              --policy-stdin) policy_stdin=1 ;;
              --help|-h) nt_help remote; return 0 ;;
              *) nt_fail "Unknown remote access preview option: $arg"; return 2 ;;
            esac
          done
          nt_require_termux || return 1
          nt_require_command python3 || return 1
          local command=(--operation remote.access.preview)
          [ "$policy_stdin" = "1" ] && command+=(--policy-stdin)
          [ "$TERNUXX_JSON" = "1" ] && command+=(--json)
          python3 "$_TN_LIB_DIR/management_service.py" "${command[@]}"
          ;;
        --help|-h) nt_help remote; return 0 ;;
        *) nt_fail "Use remote access preview [--policy-stdin]."; return 2 ;;
      esac
      ;;
    --help|-h) nt_help remote ;;
    *) nt_fail "Use remote access preview [--policy-stdin]."; return 2 ;;
  esac
}
