#!/data/data/com.termux/files/usr/bin/bash
# Quick launch commands for the Debian PRoot shell and native GUI.

_nt_launch_guest_user() {
  local distro="${1:-debian}"
  PYTHONPATH="$_TN_LIB_DIR" python3 -c \
    'import os,sys,proot_diagnostics; print(proot_diagnostics.resolve_proot_guest_user(distro=sys.argv[1], prefix=os.environ["PREFIX"]))' \
    "$distro" 2>/dev/null
}

_nt_launch_guest_shell() {
  local distro="${1:-debian}" user="${2:-root}"
  PYTHONPATH="$_TN_LIB_DIR" python3 -c \
    'import os,sys,proot_diagnostics; print(proot_diagnostics.resolve_proot_guest_shell(distro=sys.argv[1], user=sys.argv[2], prefix=os.environ["PREFIX"]))' \
    "$distro" "$user" 2>/dev/null
}

_nt_launch_verify_replay_alias() {
  local distro="$1"
  PYTHONPATH="$_TN_LIB_DIR" python3 -c \
    'import os,sys,proot_diagnostics; proot_diagnostics.verify_managed_replay_alias(sys.argv[1], os.environ["PREFIX"])' \
    "$distro" 2>/dev/null
}

_nt_guest_pulse_cookie() {
  PYTHONPATH="$_TN_LIB_DIR" python3 -c \
    'import proot_diagnostics; p=proot_diagnostics._native_pulse_cookie_path(); print(p or "")' \
    2>/dev/null
}

# Run from native Termux; inside the guest there is no proot-distro.
_nt_virgl_call() {
  python3 "$_TN_LIB_DIR/virgl_lifecycle.py" "$@"
}

_nt_virgl_ensure() {
  local display="$1" result
  result="$(_nt_virgl_call ensure --display "$display" 2>&1)" || {
    nt_fail "Could not prepare Ternuxx VirGL on $display: $result"
    return 1
  }
}

# Run from Native Termux; inside the guest there is no proot-distro.
nt_cmd_db() {
  local as_root=0 guest_user="" distro="debian" backend="zink" display=":1" option
  while [ $# -gt 0 ]; do
    option="$1"
    case "$option" in
      --root) as_root=1; shift ;;
      --user)
        [ $# -ge 2 ] || { nt_fail "--user needs a name"; return 2; }
        guest_user="$2"; shift 2 ;;
      --distro)
        [ $# -ge 2 ] || { nt_fail "--distro needs a name"; return 2; }
        distro="$2"; shift 2 ;;
      --backend)
        [ $# -ge 2 ] || { nt_fail "--backend needs zink or virgl"; return 2; }
        backend="$2"; shift 2 ;;
      --display)
        [ $# -ge 2 ] || { nt_fail "--display needs :N"; return 2; }
        display="$2"; shift 2 ;;
      --)
        shift; break ;;
      --help|-h) nt_help db; return 0 ;;
      *) break ;;
    esac
  done
  [[ "$distro" =~ ^[a-z0-9][a-z0-9._-]*$ ]] || { nt_fail "Invalid distro name."; return 2; }
  [[ -z "$guest_user" || "$guest_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || { nt_fail "Invalid guest user name."; return 2; }
  [[ "$display" =~ ^:[0-9]{1,2}$ ]] || { nt_fail "Display must be a local X11 display such as :1."; return 2; }
  [[ "$backend" = zink || "$backend" = virgl ]] || { nt_fail "Backend must be zink or virgl."; return 2; }
  local native_debian=0 native_replay=0 shell_user="" guest_shell="" shell_command="" assignment
  local virgl_guest_socket="/tmp/.ternuxx-virgl/virgl-${display#:}.sock"
  local -a session_env=()
  if [ "$distro" != debian ]; then
    _nt_launch_verify_replay_alias "$distro" || {
      nt_fail "The selected replay guest lacks an exact valid Ternuxx install receipt."
      return 1
    }
    native_replay=1
  fi
  nt_require_command proot-distro || { nt_fail "Run this from native Termux; proot-distro is not available here."; return 1; }
  local -a args=()
  if [ "$native_replay" -eq 1 ]; then
    args=(login --isolated --shared-tmp "$distro")
  else
    args=(login "$distro" --shared-tmp)
  fi
  local -a proot_env=(env -u ANDROID_ART_ROOT -u ANDROID_DATA -u ANDROID_I18N_ROOT
    -u ANDROID_ROOT -u ANDROID_RUNTIME_ROOT -u ANDROID_TZDATA_ROOT
    -u BOOTCLASSPATH -u DEX2OATBOOTCLASSPATH -u EXTERNAL_STORAGE
    -u GALLIUM_DRIVER -u MESA_LOADER_DRIVER_OVERRIDE -u TU_DEBUG
    -u MESA_VK_WSI_DEBUG -u MESA_SHADER_CACHE_DISABLE -u VTEST_SOCKET_NAME
    -u LIBGL_ALWAYS_SOFTWARE)
  if [ "$as_root" -eq 0 ]; then
    if [ -z "$guest_user" ]; then
      guest_user="$(_nt_launch_guest_user "$distro")" || guest_user=""
      [ -n "$guest_user" ] || {
        nt_fail "Could not resolve one regular guest account from the installed rootfs; pass --user NAME or --root."
        return 1
      }
    fi
    args+=(--user "$guest_user")
    shell_user="$guest_user"
  else
    shell_user="root"
  fi
  if { [ "$distro" = debian ] || [ "$native_replay" -eq 1 ]; } && [ "${PREFIX:-}" = "/data/data/com.termux/files/usr" ] && [ -n "${TERMUX_VERSION:-}" ]; then
    native_debian=1
    if [ $# -eq 0 ]; then
      guest_shell="$(_nt_launch_guest_shell "$distro" "$shell_user")" || guest_shell=""
      [[ "$guest_shell" =~ ^/[A-Za-z0-9_.+-]+(/[A-Za-z0-9_.+-]+)*$ ]] || {
        nt_fail "Could not resolve a safe login shell from the selected Debian account."
        return 1
      }
    fi
    if [ "$backend" = virgl ]; then
      nt_require_termux || return 1
      _nt_virgl_ensure "$display" || return 1
      session_env+=(-u MESA_LOADER_DRIVER_OVERRIDE -u TU_DEBUG -u MESA_VK_WSI_DEBUG
        "LIBGL_ALWAYS_SOFTWARE=true" "GALLIUM_DRIVER=virpipe"
        "VTEST_SOCKET_NAME=$virgl_guest_socket")
    else
      session_env+=("GALLIUM_DRIVER=zink" "MESA_LOADER_DRIVER_OVERRIDE=zink"
        "TU_DEBUG=sysmem,noconform" "MESA_VK_WSI_DEBUG=sw")
    fi
    session_env+=("DISPLAY=$display" "PULSE_SERVER=tcp:127.0.0.1:4713"
      "MESA_SHADER_CACHE_DISABLE=true")
    # Keep the established Debian profile baseline unchanged. Replay aliases
    # are isolated qualification guests: never persist env into their profile.
    if [ "$native_replay" -eq 0 ]; then
      args+=(--env DISPLAY=:1 --env PULSE_SERVER=tcp:127.0.0.1:4713
        --env GALLIUM_DRIVER=zink --env MESA_LOADER_DRIVER_OVERRIDE=zink
        --env TU_DEBUG=sysmem,noconform --env MESA_VK_WSI_DEBUG=sw
        --env MESA_SHADER_CACHE_DISABLE=true)
    fi
    _nt_use audio || return 1
    nt_audio_ensure || true
    local pulse_cookie
    pulse_cookie="$(_nt_guest_pulse_cookie)" || pulse_cookie=""
    if [ -n "$pulse_cookie" ]; then
      args+=(--bind "$pulse_cookie:/tmp/.ternuxx-pulse-cookie"
        --env PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie)
      session_env+=("PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie")
    else
      nt_warn "Native PulseAudio cookie is unavailable; guest audio may not connect."
    fi
    if [ "$backend" = zink ] || [ "$native_replay" -eq 0 ]; then
      if [ -c /dev/kgsl-3d0 ]; then args+=(--bind /dev/kgsl-3d0:/dev/kgsl); fi
      if [ -d /dev/dri ]; then args+=(--bind /dev/dri); fi
    fi
  elif [ "$backend" = virgl ]; then
    nt_fail "VirGL handoff requires the Native Termux host; it cannot be configured from PRoot."
    return 1
  fi

  if [ "$native_debian" -eq 1 ]; then
    if [ $# -gt 0 ]; then
      args+=(-- /usr/bin/env "${session_env[@]}" "$@")
    else
      # Load the normal shared login profile first; apply the selected backend
      # only to this interactive child shell.
      shell_command="exec /usr/bin/env"
      while [ ${#session_env[@]} -gt 0 ]; do
        assignment="${session_env[0]}"
        session_env=("${session_env[@]:1}")
        if [ "$assignment" = "-u" ]; then
          [ ${#session_env[@]} -gt 0 ] || { nt_fail "Invalid session environment."; return 1; }
          shell_command+=" -u ${session_env[0]}"
          session_env=("${session_env[@]:1}")
        else
          [[ "$assignment" =~ ^[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9_./:+,-]+$ ]] || {
            nt_fail "Invalid session environment value."
            return 1
          }
          shell_command+=" '$assignment'"
        fi
      done
      shell_command+=" '$guest_shell' -i"
      args+=(-- "$guest_shell" -l -c "$shell_command")
    fi
  elif [ $# -gt 0 ]; then
    args+=(-- "$@")
  fi
  exec "${proot_env[@]}" proot-distro "${args[@]}"
}

# Native Termux desktop; thin aliases over the existing lifecycle commands.
nt_cmd_gui_monitor() {
  local action="${1:-status}" operation flag value
  [ $# -eq 0 ] || shift
  local -a args=()
  case "$action" in
    --help|-h) nt_help gui; return 0 ;;
    service)
      nt_require_termux || return 1
      nt_require_command python3 || return 1
      python3 "$_TN_LIB_DIR/gui_monitoring.py" service "$@"
      return $? ;;
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
