# =============================================================================
#  Ternuxx CLI help
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

_nt_help_raw() {
  local cmd="${1:-}"
  case "$cmd" in
    "")
      cat <<'EOF'
Ternuxx — native Termux workstation management

Usage:
  tx <command> [options]

Quick launch:
  tx db              Open the configured Debian PRoot shell
  tx gui             Open the Native Termux GTK management center
  tx start           Start the native Termux:X11/XFCE desktop
  tx tui             Interactive terminal management
  tx web             Open the shared Web UI in Android browser

Commands:
  start       Start the Native Termux:X11/XFCE session
  stop        Stop recorded native desktop
  restart     Restart native desktop
  status      Show desktop status
  check       Inspect device and package readiness
  info        Show system, renderer, Vulkan, package, and session information
  doctor      Run diagnostic checks
  mng         Shared management operations and local Web service
  proot       Inspect and manage PRoot integrations
  audio       Manage Native PulseAudio used by Debian PRoot
  ssh         Inspect and manage the fixed native SSH service
  checkpoint  Prepare or verify reboot-continuity records
  remote      Preview off-home access policy
  reboot      Inspect or manage reboot-test checkpoints
  boot        Inspect Termux:Boot availability and profile
  wakelock    Inspect or manage Wake Lock ownership
  install     Preview or apply native desktop package setup
  backup      Backup operations
  recovery    Recovery journal operations
  restore     Restore preview or apply
  guides      Show documentation links
  help        Show this help

Options:
  --json      Machine-readable output
  --verbose   Extra diagnostic messages
  --quiet     Suppress informational output
  --help, -h  Show command help

Examples:
  tx check
  tx info
  tx start
  tx mng app launch files
  tx tui
  tx web
  tx ssh inspect --json
  tx proot status
  tx backup list
  tx recovery status
  tx recovery resolve OPERATION_ID
  tx remote access preview
  tx proot verify --distro debian --guest-user-from rootfs --display :1 --backend zink

Safety:
  start/stop/restart change process and session state. install --yes requires
  an exact preview plan ID. Recovery apply operations require their preview ID.
  Remote access defaults to disabled and never enables public ingress.

Short command spellings remain accepted as aliases. Help uses the full names.
EOF
      ;;
    remote)
      cat <<'EOF'
tx remote access preview — Preview optional off-home access policy

Without input, reports remote access disabled. With --policy-stdin, reads one
secret-free schema-v2 desired-policy JSON object from stdin. Preview never
persists configuration, resolves credential references, contacts a network,
starts a service, or enables public ingress. Private transport stays unavailable
until an owner-selected adapter and its device/network security gates are met.
Pass --json before the command for machine-readable output.
EOF
      ;;
    management)
      cat <<'EOF'
tx mng center [install] — Open/install the native GTK management app
tx mng catalog list — Browse shared categories and resources
tx mng proot status — Inspect installed guest and Ternuxx session ownership
tx mng proot profiles list|show — Inspect validated headless and interactive profiles
tx mng proot sessions list|show|health — Inspect owned sessions, liveness, exit and attachment capability
tx mng proot start --profile ID — Preview a start; repeat with --yes --plan-id ID to confirm
tx mng proot stop SESSION_ID — Preview exact-session stop; repeat with --yes --plan-id ID to confirm
The debian-interactive profile requires a TTY and opens a foreground login shell; it does not start GUI or services.
tx mng hermes status — Inspect optional Hermes scheduler (read-only)
tx mng cron status/start/stop — Inspect or explicitly manage the lease-guarded scheduler
tx mng cron jobs list|show|validate|next-runs|create|update|enable|disable|remove — Manage validated job definitions
tx mng boot cron status|validate — Inspect the opt-in official Termux:Boot Cron entry
tx mng boot cron preview {enable|disable} — Preview exact script changes
tx mng boot cron enable|disable --yes --plan-id ID — Apply the reviewed boot-script plan
tx mng timezone status|list — Inspect configured timezone and available IANA zones
tx mng timezone set IANA_NAME — Persist an explicitly selected timezone
tx mng doctor [--graphics] — Run read-only Doctor via the shared service
tx mng app launch APP_ID — Launch a named PRoot app on native X11
tx mng shortcuts list — View PRoot app launchers
tx mng shortcuts plan {add|remove} APP_ID — Preview a launcher change
tx mng shortcuts apply {add|remove} APP_ID --plan-id ID --yes — Confirm the exact preview
tx mng http serve — Run the read-only management API in foreground
tx web — Open the browser UI over the same shared service

The Web UI binds only to 127.0.0.1 (default port 8765), copies the one-time
bootstrap secret to the Termux clipboard, opens the local browser, and runs until Ctrl-C. The secret is not saved. If clipboard copy fails,
the server stops without revealing it; use --show-secret-on-clipboard-failure
for the explicit private-terminal fallback. The browser client uses the shared management service. It can read catalogued diagnostics, edit GUI Activity-monitoring policy, and start/stop/restart the verified native desktop after confirmation. Other mutations stay unavailable until their preview and authorization flows are implemented.
EOF
      ;;
    start)
      cat <<'EOF'
tx start — Start the native Termux XFCE session

Starts the Ternuxx-owned Termux:X11 server and XFCE session on an
available display, keeps Android Activity launch disabled by default, and records
session state and logs under the configured state directory. If Android blocks
the request, open the app manually. A successful request does not prove that
the GUI is visible. It attempts to start Native PulseAudio; failure does not
block desktop startup. `tx stop` leaves audio running for active PRoot clients.

Requirements include Termux, termux-x11, dbus-launch, xfce4-session, python3,
and nohup. Use --display N to request a specific display number; startup fails
if its socket or lock is already present. Without that option, the command
searches displays :0 through :10.

This command starts processes and writes private session state/log files.
If startup fails, inspect the reported log and state paths. Do not remove X11
sockets or stop untracked processes. The Android Activity is never launched by status or diagnostic requests. `tx gui monitor status` is read-only; configure polling with `tx gui monitor configure --enabled on --interval N seconds|minutes|hours`. Monitoring stays disabled by default.
EOF
      ;;
    stop)
      cat <<'EOF'
tx stop — Stop the recorded native desktop session

Stops only the supervisor or child processes whose PID, process start time,
and command marker match the saved session record. It sends SIGTERM and does
not use broad process matching or SIGKILL. Session state and logs are retained.

This command changes process and session state. If ownership cannot be
verified, it does not signal that process; inspect the session record and log.
The recorded target passed stop/repeat and unrelated PRoot-session preservation checks;
other Android/Termux builds still need their own process-tree validation.
EOF
      ;;
    restart)
      cat <<'EOF'
tx restart — Restart the native desktop session

Runs stop, then start. It changes process and session state, and start options
such as --display N are accepted. See 'tx stop --help' and
'tx start --help' for lifecycle boundaries and requirements.
EOF
      ;;
    status)
      cat <<'EOF'
tx status — Inspect the recorded native desktop session

Reads session state and verifies recorded process identities. It does not
start or stop processes. GUI visibility is reported as unknown because the
Termux:X11 Android app's visible state is not inferred by the CLI.
EOF
      ;;
    db)
      cat <<'EOF'
tx db — Open a Debian PRoot shell (independent of any desktop)

  tx db                  # as the configured guest user
  tx db --root           # as root
  tx db --user NAME      # as an explicit guest user
  tx db -- CMD [ARG ...] # run one command instead of a shell
  tx db --distro NAME    # another installed proot-distro guest

Run from native Termux. Ternuxx ensures its Native PulseAudio endpoint and
passes the loopback server and private cookie path to Debian. Audio failure is
reported but does not block the shell. The guest user is resolved from the installed Debian account database; ambiguous accounts fail closed. It starts no desktop or X11 service. Ternuxx filters inherited Android/ART host variables, then passes only explicit display, audio, and selected graphics settings; proot-distro writes those guest settings to its generated login profile.
EOF
      ;;
    audio)
      cat <<'EOF'
tx audio — Manage the Native PulseAudio server used by PRoot

  tx audio status     Inspect Ternuxx ownership and authenticated loopback readiness
  tx audio start      Start one identity-checked Native server if no owner conflicts
  tx audio stop       Stop only the exact process recorded as Ternuxx-owned
  tx audio restart    Restart only the exact Ternuxx-owned server

The service listens only on 127.0.0.1:4713 and uses the Native PulseAudio
cookie for Debian clients. Live or unknown servers and lock artifacts are
preserved. tx start, tx gui, and tx db attempt an idempotent start; audio
failure never prevents the desktop or PRoot CLI from opening. tx stop leaves
audio running so active PRoot clients are not disconnected.
EOF
      ;;
    web)
      cat <<'EOF'
tx web — Open the shared local management Web UI

Starts a loopback-only service, copies the one-time secret to the Termux clipboard,
and opens the Android browser. Clipboard failure stops safely without revealing
the secret; use --show-secret-on-clipboard-failure for an explicit terminal
fallback. Press Ctrl-C to stop. The Web client uses the shared management API
with its authorized desktop, monitoring-policy, and managed SSH 8023 operations.
EOF
      ;;
    tui)
      cat <<'EOF'
tx tui — Interactive terminal client

Overview, PRoot, SSH, and recovery views use the shared typed service. Press
1–5 to switch views, arrows/j/k to scroll, PageUp/PageDown for larger jumps,
Enter to refresh, l to choose and launch a named PRoot app, o to run an
allowlisted operation, and q to exit. The guided launch asks for the X11 session
and display, then requires confirmation. Text wraps to fit the terminal width.
EOF
      ;;
    gui)
      cat <<'EOF'
tx gui — Native Termux GTK management center

  tx gui                              Open the installed GTK management center
  tx gui start|stop|restart|status    Preserve native desktop lifecycle aliases
  tx gui monitor status|enable|disable|configure OPTIONS

Run from Native Termux with a local X11 display selected. Install the graphical
client with 'tx mng center install'. Desktop lifecycle remains available as
'tx start|stop|restart|status'; it does not enter Debian PRoot or launch the
Termux:X11 Android Activity. Monitoring is configured separately.
EOF
      ;;
    checkpoint)
      cat <<'EOF'
tx checkpoint — Prepare or verify reboot continuity evidence

Native Termux only. Records a private checkpoint beneath the configured
Ternuxx state directory. Verification compares boot IDs when available and
records service readiness as not collected until a separate live check runs.
Pending tests are never executed automatically.

  tx checkpoint prepare --test-id <id> [--pending-test <id> ...]
  tx checkpoint verify <checkpoint-id>

This writes private evidence to the native Termux home. It does not configure
boot startup, start services, acquire Wake Lock, or interact with PRoot.
EOF
      ;;
    ssh)
      cat <<'EOF'
tx ssh inspect/start/stop - Native SSH diagnostics and fixed Runit service control

  tx ssh inspect
  tx proot status # Inventory installed guests without entering them
  tx ssh start                         # read-only preview
  tx ssh start --yes --plan-id <id>    # apply exact preview
  tx ssh stop                          # read-only preview
  tx ssh stop --yes --plan-id <id>     # apply exact preview

Reports whether OpenSSH/configuration is present, whether sshd accepts the
current config, allowlisted effective authentication/bind policy, observed
TCP listeners and whether procfs permitted reading them, process presence,
Termux:Boot directory presence, and whether a runit command is available. It
does not read key or password files, display raw config, or test authenticated
connectivity. Start/stop preview and apply control only the fixed Ternuxx
Runit unit after exact service-definition identity verification. Apply requires
--yes and its preview plan ID, journals before sv up/down, and verifies the
resulting Runit state. Stop can disconnect clients using the managed SSH port.
The command does not change SSH configuration or control PRoot SSH.
EOF
      ;;
    proot)
      cat <<'EOF'
tx proot status — Read-only installed guest inventory
tx proot gui {start|status|stop} — legacy session status/stop; separate :0 start disabled
tx proot verify --distro debian (--guest-user USER|--guest-user-from rootfs) --display :N --backend zink|virgl

--backend is the expected renderer class for this read-only probe; it does not switch drivers.

gui start currently fails closed because a full Debian desktop must be nested
inside the native Termux :1 desktop; it must not open a separate :0 Activity.
Specific GUI apps remain available through tx mng app launch APP_ID. No guest
reinstall or rootfs replacement is part of this route. Status lists installed
distributions. Verify enters Debian only to run a fixed Ternuxx read-only
display/audio/renderer probe. The rootfs source resolves the unique ordinary
non-root account from Debian passwd; unsafe paths or ambiguous accounts fail
closed. This route does not invoke the separate Ternux CLI or change guest
packages, services, or desktop lifecycle.
EOF
      ;;
    reboot)
      cat <<'EOF'
tx reboot — Native reboot-test evidence (no reboot command is provided)

  tx reboot status [test-id]
  tx reboot prepare --test-id <id> --baseline-json <object>
  tx reboot verify <test-id>
  tx reboot resume-info <test-id>

Preparation writes a private, atomic checkpoint and always records
NOT_READY. It does not arm Termux:Boot, start/stop services, or reboot.
Verification compares boot IDs and records evidence; it never resumes tasks.
EOF
      ;;
    boot)
      cat <<'EOF'
tx boot status — Read-only Termux:Boot capability inspection
tx boot profile status
tx boot profile preview <cli-only|native|proot|hybrid>
tx mng boot cron status|validate
tx mng boot cron preview {enable|disable}
tx mng boot cron enable|disable --yes --plan-id PLAN_ID
tx boot gui <on|off> [--yes]
tx boot enable --profile <mode> [--yes]
tx boot disable [--yes]

The default profile is cli-only, so GUI startup after reboot stays off.
Use the direct GUI toggle; it previews by default and --yes applies the plan:
  tx boot gui on
  tx boot gui on --yes
  tx boot gui off
  tx boot gui off --yes
These commands preview first; --yes applies only the shown Ternuxx-owned file
changes and preserves unrelated boot scripts. Native starts Ternuxx-owned
X11/XFCE processes; opening the Android Termux:X11 app and visible GUI remain
separate. Android boot delivery is independently unverified. PRoot and hybrid
profiles remain blocked until their ownership-aware adapter is implemented.
EOF
      ;;
    wakelock)
      cat <<'EOF'
tx wakelock status — Read-only Wake Lock capability inspection

Reports command availability and the ownership limitation. It never invokes
termux-wake-lock or termux-wake-unlock; Android lock-holder state remains
unknown unless a verified platform API is added.

  tx wakelock acquire <owner>
  tx wakelock release <owner>
  tx wakelock acquire native.sshd --persistent

Acquire/release tracks a Ternuxx-owned lease in private native state. Only the
owner process can release its non-persistent lease. Persistent leases are
reserved for the native SSH service and must be released by that service's
manager. Android still exposes one app-global lock; unrelated Termux clients
are outside this coordinator.
EOF
      ;;
    install)
      cat <<'EOF'
tx install — Preview or install Native workstation prerequisites

By default, validates recent official Termux package indexes and prints a
constrained APT simulation. It does not refresh package indexes or change
packages. The plan includes the Native PRoot manager and base desktop package set; it
does not install, replace, or modify a Debian rootfs. It refuses removals,
upgrades, recommendations, or packages sourced outside official Termux repos.

Each full dependency preview is saved under the private Ternuxx state directory
at install-transactions/. --yes rebuilds the plan, displays it, then applies it;
a successful apply gets its own record. APT may leave some packages installed
if an install fails. Ternuxx does not automatically remove packages or claim a
rollback; inspect APT output/history and review a fresh preview before retrying.
This changes the Termux environment. Install the Termux:X11 Android app separately.
EOF
      ;;
    check)
      cat <<'EOF'
tx check — Inspect device readiness

Reports available commands, package readiness, and Termux:X11 presence. It
does not install packages or intentionally modify files. Device interfaces
queried by diagnostic tools may have their own runtime behavior.
EOF
      ;;
    doctor)
      cat <<'EOF'
tx doctor — Run the available diagnostics

Runs the read-only Doctor report with stable finding IDs, severity, scope, and
suggested actions. Use --json for structured output. Add --graphics to probe the
current DISPLAY; this does not start a desktop/workload, and detection alone
does not prove accelerated execution.
EOF
      ;;
    info)
      cat <<'EOF'
tx info — Show system information

Shows available renderer, Vulkan, package, and recorded session information.
Missing diagnostic tools are reported as unavailable; hardware detection is
not proof of a verified GPU workload.
EOF
      ;;
    guides)
      printf '%s\n' \
        'Ternuxx guides:' \
        '  Installation: https://github.com/soobujmiah/ternuxx/blob/main/docs/INSTALLATION.md' \
        '  Architecture: https://github.com/soobujmiah/ternuxx/blob/main/docs/ARCHITECTURE.md' \
        '  Troubleshooting: see the repository docs/ directory' \
        '' 'Opening these links is left to the user; this command installs nothing.'
      ;;
    *)
      nt_fail "No help available for '$cmd'. Run 'tx help' for usage."
      return 1
      ;;
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
