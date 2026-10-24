# =============================================================================
#  Ternuxx CLI help — Native Termux only
# =============================================================================
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

_nt_help_raw() {
  local cmd="${1:-}"
  case "$cmd" in
    "") cat <<'EOF'
Ternuxx — Native Termux workstation management

Usage: tx <command> [options]

Quick launch:
  tx gui             Open the Native GTK management center
  tx start           Start the Native Termux:X11/XFCE desktop
  tx tui             Open interactive terminal management
  tx web             Open the authenticated local Web UI
  tx doctor          Run Native environment health checks
  tx guides          Open the interactive setup guide

Commands by task:
  Desktop: start, stop, restart, status, gui, tui, web
  Graphics: graphics, info, check, doctor
  Local AI: ai (pinned Native CPU model workflow)
  Software: app (curated Native package catalog)
  Management: mng, audio, ssh, remote
  Recovery: checkpoint, reboot, boot, wakelock, backup, recovery, restore
  Setup: install
  Reference: guides, help

Use `tx help NAME` for command options. Common aliases: up=start, dn=stop,
rs=restart, st=status, ck=check, inf=info, doc=doctor, mg=mng.
Options: --json, --verbose, --quiet, --help
Install and recovery changes require an exact preview plan. Remote access is
disabled by default.
EOF
      ;;
    proot|db|pgui|virgl|terminal)
      cat <<'EOF'
PRoot and guest-terminal support have been removed from Ternuxx.
Ternuxx runs directly in Native Termux. Use `tx help`, `tx tui`, or `tx guides`.
EOF
      ;;
    start) cat <<'EOF'
tx start — Start the Native Termux:X11/XFCE desktop
The command starts only the verified Native desktop process group and records
private session state. It does not open the Android X11 Activity automatically.
Run `tx status` to inspect the saved session and `tx stop` to stop it.
EOF
      ;;
    stop) cat <<'EOF'
tx stop — Stop the recorded Native desktop session
Only recorded process identities are stopped, using SIGTERM. Unknown or changed
processes are preserved. Session state and logs remain available for diagnosis.
EOF
      ;;
    restart) cat <<'EOF'
tx restart — Stop, then start the Native desktop
This changes process and session state. See `tx stop --help` and
`tx start --help` for lifecycle details.
EOF
      ;;
    status) cat <<'EOF'
tx status — Inspect the Native desktop session
Reads saved state and verifies recorded process identities. It does not start
or stop processes. GUI visibility is reported as unknown unless observed.
EOF
      ;;
    install) cat <<'EOF'
tx install preview — Review Native Termux prerequisite packages
tx install update preview — Review Native Ternuxx core updates
tx install apply --yes --plan-id ID — Apply the exact saved Native package plan
No guest, Debian, or PRoot packages are installed by this plan.
EOF
      ;;
    ssh) cat <<'EOF'
tx ssh inspect — Inspect Native SSH state
tx ssh start|stop|restart — Preview, then confirm with --yes --plan-id ID
SSH key management distinguishes private keys from public authorized keys.
EOF
      ;;
    remote) cat <<'EOF'
tx remote access preview — Inspect optional remote-access policy
Remote access is disabled by default. Preview does not persist settings, contact
a network, start a service, or enable public ingress.
EOF
      ;;
    graphics) cat <<'EOF'
tx graphics native status|enable --prefix PATH|disable
Select an extracted Native KGSL Mesa candidate for future desktop sessions.
GPU inference is not implied by a detected device or installed library.
EOF
      ;;
    web) cat <<'EOF'
tx web — Open the authenticated Native Termux management Web UI
The service binds to loopback and uses the shared management API for Native
desktop, graphics, SSH, Cron, and timezone operations. Browser choices are
Android or an installed Native Termux browser. Press Ctrl-C to stop the service.
EOF
      ;;
    management|mng) cat <<'EOF'
tx mng center [install] — Open or install the Native GTK app
tx mng catalog list — Browse supported Native resources
tx mng logs list|read SOURCE_ID — Read bounded Ternuxx logs
tx mng cron ... — Manage the Native scheduler and jobs
tx mng timezone ... — Inspect or set the system timezone
tx mng graphics ... — Inspect Native graphics
tx mng http serve — Run the authenticated loopback API
EOF
      ;;
    tui) cat <<'EOF'
tx tui — Interactive Native Termux management
Use arrows or the displayed keys to browse resources and review supported
Native actions. Mutating operations use shared preview/confirmation rules.
EOF
      ;;
    app) cat <<'EOF'
tx app list — List the curated Native Termux apps and current package state
tx app preview APP_ID install|update|remove — Simulate the exact official package transaction
tx app apply APP_ID ACTION --plan-id ID [--confirm ACTION] — Apply a saved plan
tx app run directory-tree HOME_PATH - Bounded read-only HOME file/directory handoff
Only htop, tmux, and tree are selectable. Apply requires a current plan and
exact typed INSTALL, UPDATE, or REMOVE confirmation. No autoremove is used.
File handoff accepts only regular files/directories below HOME; file contents are not read.
EOF
      ;;
    ai) cat <<'EOF'
tx ai status — Inspect llama.cpp runtime and pinned local model state
tx ai setup — Interactive runtime preflight, model preview, and optional CPU run
tx ai model preview — Show the exact 429 MB download, checksum, license, and target
tx ai model install — Preview first; type DOWNLOAD to install the pinned model
tx ai model remove-preview / tx ai model remove — Preview, then type REMOVE
tx ai run — Read a local prompt from terminal/stdin; CPU-only, bounded to 128 tokens
The Termux-owned llama-cpp runtime is separate; Ternuxx never installs packages here.
EOF
      ;;
    doctor) cat <<'EOF'
tx doctor [--graphics] — Run read-only Native Termux health checks
Graphics probes are optional and report observed evidence without claiming
workload acceleration from library or device-node presence alone.
EOF
      ;;
    *) nt_fail "No help available for '$cmd'. Run 'tx help' for Native Termux usage."; return 1 ;;
  esac
}

nt_cmd_help() { nt_help "${1:-}"; }

# Color is used only for an interactive capable terminal. Redirected help,
# scripts, and terminals opting out with NO_COLOR receive plain text.
nt_help() {
  local body line first=1
  body="$(_nt_help_raw "$1")" || return $?
  if [ ! -t 1 ] || [ -n "${NO_COLOR:-}" ] || [ "${TERM:-dumb}" = dumb ]; then
    printf '%s\n' "$body"
    return 0
  fi
  while IFS= read -r line; do
    if [ "$first" -eq 1 ] && [[ "$line" == Ternuxx* ]]; then
      printf '\033[1;36m╭────────────────────────────────────────────────────────────────────╮\033[0m\n'
      printf '\033[1;36m│\033[0m \033[1;97m%-66s\033[0m \033[1;36m│\033[0m\n' "$line"
      printf '\033[1;36m╰────────────────────────────────────────────────────────────────────╯\033[0m\n'
      first=0
      continue
    fi
    first=0
    case "$line" in
      Usage:*|Options:*|Commands:*|Examples:*|Safety:*|Quick\ launch:*|Short\ forms:*)
        printf '\033[1;35m%s\033[0m\n' "$line" ;;
      "  "*)
        printf '  \033[1;32m%s\033[0m\n' "${line#  }" ;;
      *) printf '%s\n' "$line" ;;
    esac
  done <<< "$body"
}
