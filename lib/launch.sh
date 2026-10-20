#!/data/data/com.termux/files/usr/bin/bash
# Quick launch commands for the Debian PRoot shell and native GUI.

_nt_launch_guest_user() {
  local distro="${1:-debian}"
  PYTHONPATH="$_TN_LIB_DIR" python3 -c \
    'import os,sys,proot_diagnostics; print(proot_diagnostics.resolve_proot_guest_user(distro=sys.argv[1], prefix=os.environ["PREFIX"]))' \
    "$distro" 2>/dev/null
}

_nt_guest_pulse_cookie() {
  PYTHONPATH="$_TN_LIB_DIR" python3 -c \
    'import proot_diagnostics; p=proot_diagnostics._native_pulse_cookie_path(); print(p or "")' \
    2>/dev/null
}

# Run from native Termux; inside the guest there is no proot-distro.
nt_cmd_db() {
  local as_root=0 guest_user="" distro="debian"
  while [ $# -gt 0 ]; do
    case "$1" in
      --root) as_root=1; shift ;;
      --user)
        [ $# -ge 2 ] || { nt_fail "--user needs a name"; return 2; }
        guest_user="$2"; shift 2 ;;
      --distro)
        [ $# -ge 2 ] || { nt_fail "--distro needs a name"; return 2; }
        distro="$2"; shift 2 ;;
      --) shift; break ;;
      *) break ;;
    esac
  done
  [[ "$distro" =~ ^[a-z0-9][a-z0-9._-]*$ ]] || { nt_fail "Invalid distro name."; return 2; }
  nt_require_command proot-distro || { nt_fail "Run this from native Termux; proot-distro is not available here."; return 1; }
  local args=(login "$distro" --shared-tmp)
  local -a proot_env=(env -u ANDROID_ART_ROOT -u ANDROID_DATA -u ANDROID_I18N_ROOT
    -u ANDROID_ROOT -u ANDROID_RUNTIME_ROOT -u ANDROID_TZDATA_ROOT
    -u BOOTCLASSPATH -u DEX2OATBOOTCLASSPATH -u EXTERNAL_STORAGE)
  if [ "$as_root" -eq 0 ]; then
    if [ -z "$guest_user" ]; then
      guest_user="$(_nt_launch_guest_user "$distro")" || guest_user=""
      [ -n "$guest_user" ] || {
        nt_fail "Could not resolve one regular guest account from the installed rootfs; pass --user NAME or --root."
        return 1
      }
    fi
    [[ "$guest_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || { nt_fail "Invalid guest user name."; return 2; }
    args+=(--user "$guest_user")
  fi
  if [ "$distro" = debian ] && [ "${PREFIX:-}" = "/data/data/com.termux/files/usr" ] && [ -n "${TERMUX_VERSION:-}" ]; then
    _nt_use audio || return 1
    nt_audio_ensure || true
    local pulse_cookie display="${DISPLAY:-:1}"
    pulse_cookie="$(_nt_guest_pulse_cookie)" || pulse_cookie=""
    args+=(--env "DISPLAY=$display" --env PULSE_SERVER=tcp:127.0.0.1:4713
      --env GALLIUM_DRIVER=zink --env MESA_LOADER_DRIVER_OVERRIDE=zink
      --env TU_DEBUG=sysmem,noconform --env MESA_VK_WSI_DEBUG=sw
      --env MESA_SHADER_CACHE_DISABLE=true)
    if [ -n "$pulse_cookie" ]; then
      args+=(--bind "$pulse_cookie:/tmp/.ternuxx-pulse-cookie"
        --env PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie)
    else
      nt_warn "Native PulseAudio cookie is unavailable; guest audio may not connect."
    fi
    if [ -c /dev/kgsl-3d0 ]; then args+=(--bind /dev/kgsl-3d0:/dev/kgsl); fi
    if [ -d /dev/dri ]; then args+=(--bind /dev/dri); fi
  fi
  [ $# -eq 0 ] || args+=(-- "$@")
  exec "${proot_env[@]}" proot-distro "${args[@]}"
}

# Native Termux desktop; thin aliases over the existing lifecycle commands.
nt_cmd_gui_monitor() {
  local action="${1:-status}" operation flag value
  [ $# -eq 0 ] || shift
  local -a args=()
  case "$action" in
    --help|-h) nt_help gui; return 0 ;;
    status) operation="desktop.monitor.status" ;;
    enable) operation="desktop.monitor.configure"; args+=(--monitor-enabled) ;;
    disable) operation="desktop.monitor.configure"; args+=(--monitor-disabled) ;;
    configure)
      operation="desktop.monitor.configure"
      while [ "$#" -gt 0 ]; do
        flag="$1"; shift
        case "$flag" in
          --enabled|--activity-launch|--focus-check)
            [ "$#" -ge 1 ] || { nt_fail "$flag requires on or off"; return 2; }
            value="$1"; shift
            case "$flag:$value" in
              --enabled:on) args+=(--monitor-enabled) ;;
              --enabled:off) args+=(--monitor-disabled) ;;
              --activity-launch:on) args+=(--monitor-activity-launch) ;;
              --activity-launch:off) args+=(--monitor-no-activity-launch) ;;
              --focus-check:on) args+=(--monitor-focus-check) ;;
              --focus-check:off) args+=(--monitor-no-focus-check) ;;
              *) nt_fail "$flag accepts on or off"; return 2 ;;
            esac ;;
          --interval)
            [ "$#" -ge 2 ] || { nt_fail "--interval requires a value and unit"; return 2; }
            args+=(--monitor-interval "$1" --monitor-unit "$2"); shift 2 ;;
          *) nt_fail "Unknown GUI monitoring option: $flag"; return 2 ;;
        esac
      done ;;
    *) nt_fail "Use gui monitor [status|enable|disable|configure options]"; return 2 ;;
  esac
  nt_require_termux || return 1
  nt_require_command python3 || return 1
  python3 "$_TN_LIB_DIR/management_service.py" --operation "$operation" "${args[@]}" --json
}

nt_cmd_gui() {
  local action="${1:-open}"
  [ $# -eq 0 ] || shift
  if [ "$action" = "monitor" ]; then nt_cmd_gui_monitor "$@"; return $?; fi
  case "$action" in
    open|center)
      [ $# -eq 0 ] || { nt_fail "Usage: tx gui"; return 2; }
      _nt_use management || return 1
      nt_cmd_management center
      ;;
    start|stop|restart|status)
      # Preserve the historical explicit desktop lifecycle subcommands.
      _nt_use desktop || return 1
      case "$action" in
        start)   nt_cmd_start "$@" ;;
        stop)    nt_cmd_stop "$@" ;;
        restart) nt_cmd_restart "$@" ;;
        status)  nt_cmd_status "$@" ;;
      esac
      ;;
    *) nt_fail "Use 'tx gui' to open the Native management center, or tx gui [start|stop|restart|status] for desktop lifecycle."; return 2 ;;
  esac
}
