# =============================================================================
#  Ternuxx CLI help (the ternuxx command name is retained for compatibility)
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

nt_help() {
  local cmd="${1:-}"
  case "$cmd" in
    "")
      cat <<'EOF'
Ternuxx — native Termux desktop management

Usage:
  ternuxx <command> [options]

Legacy compatibility alias: nativeternux <command> [options]

Commands:
  check     Inspect device and package readiness (read-only)
  info      Show system, renderer, Vulkan, package, and session information
  start     Start the Native Termux:X11/XFCE session
  stop      Stop only the recorded Ternuxx-owned session
  restart   Stop the recorded session, then start it again
  status    Show recorded session and process-identity status
  doctor    Run the available diagnostic checks
  checkpoint Prepare or verify a private reboot-continuity record (native only)
  ssh       inspect or manage the fixed native SSH service
  remote    preview optional off-home private-access policy (read-only)
  management  Manage shared services and PRoot shortcuts, or run the optional local API
  proot     inspect PRoot inventory or verify an explicitly selected Ternux guest
  reboot    inspect or manage a bounded reboot-test checkpoint
  boot      inspect Termux:Boot availability (read-only)
  wakelock  inspect Wake Lock command/ownership limits (read-only)
  install   Preview the base desktop package transaction
  guides    Show documentation links
  help      Show this help
  --version Show version

Options:
  --json      Machine-readable output
  --verbose   Extra diagnostic messages
  --quiet     Suppress informational output
  --help, -h  Show help

Examples:
  ternuxx check             # Inspect readiness; no package changes
  ternuxx info              # Show renderer and Vulkan information
  ternuxx start             # Starts X11/XFCE and writes session state
  ternuxx stop              # Stops only processes verified from session state
  ternuxx install           # Preview packages; does not install
  ternuxx checkpoint prepare --test-id reboot-check
  ternuxx ssh inspect --json
  ternuxx remote access preview
  ternuxx management catalog list                # Shared providers, operations, and support status
  ternuxx management doctor [--graphics]         # Read-only system Doctor through shared service
  ternuxx management app launch files            # Launch a named PRoot GUI app
  ternuxx management shortcuts list              # Provider-aware PRoot app shortcuts
  ternuxx management shortcuts plan add files    # Preview a menu change
  ternuxx management http serve --port 8765      # Foreground, read-only, loopback only
  printf '%s\n' '{"schema_version":2,"mode":"disabled","public_ingress":false}' | ternuxx remote access preview --policy-stdin
  ternuxx proot status
  ternuxx boot status
  ternuxx wakelock status
  ternuxx reboot status
  ternuxx backup create --name NAME # Preview, then confirm with its plan ID
  ternuxx backup list
  ternuxx backup inspect BACKUP_ID
  ternuxx recovery status
  ternuxx recovery inspect OPERATION_ID
  ternuxx recovery resolve OPERATION_ID # Reconcile a supported desktop, service, boot, backup, or profile-restore journal
  ternuxx recovery rollback OPERATION_ID # Preview, then confirm with --plan-id
  ternuxx restore --preview BACKUP_ID
  ternuxx restore BACKUP_ID --yes --plan-id ID
  # Backups and restore rollback cover only the validated native boot profile.
  # Recovery resolve updates only a reviewed journal; it never signals desktop processes or edits backups.
  ternuxx install --preview # Save an exact dependency plan and show its ID
  ternuxx install --yes --plan-id ID  # Apply only that unchanged saved plan

Safety:
  start/stop/restart change process and session state. install --yes requires
an exact saved preview ID and installs
  packages. Review the command-specific help before running either operation.
  Lifecycle behavior is verified only on the recorded target; other devices may differ.
EOF
      ;;
    remote)
      cat <<'EOF'
ternuxx remote access preview — Preview optional off-home access policy

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
ternuxx management catalog list — List shared domains and providers
ternuxx management doctor [--graphics] — Run read-only Doctor via the shared service
ternuxx management app launch APP_ID — Launch a named PRoot app on native X11
ternuxx management shortcuts list — View PRoot app launchers
ternuxx management shortcuts plan {add|remove} APP_ID — Preview a launcher change
ternuxx management shortcuts apply {add|remove} APP_ID --plan-id ID --yes — Confirm the exact preview
ternuxx management http serve — Run the optional read-only API in the foreground

This explicit command binds only 127.0.0.1 (default port 8765), prints one
ephemeral bootstrap secret to the controlling terminal, and runs until Ctrl-C.
The secret is not saved; restart the command to establish a new browser/client
session. The API grants read-only scopes and does not start at boot or manage
ADB/Shizuku. Mutations, browser UI, fixed-port device qualification, and
off-home access are not enabled by this command.
EOF
      ;;
    start)
      cat <<'EOF'
ternuxx start — Start the native Termux XFCE session

Starts the Ternuxx-owned Termux:X11 server and XFCE session on an
available display, then requests the Termux:X11 Android activity and records
session state and logs under the configured state directory. If Android blocks
the request, open the app manually. A successful request does not prove that
the GUI is visible. This command does not start or stop PulseAudio.

Requirements include Termux, termux-x11, dbus-launch, xfce4-session, python3,
and nohup. Use --display N to request a specific display number; startup fails
if its socket or lock is already present. Without that option, the command
searches displays :0 through :10.

This command starts processes and writes private session state/log files.
If startup fails, inspect the reported log and state paths. Do not remove X11
sockets or stop untracked processes. Physical-device behavior is not yet
release-qualified.
EOF
      ;;
    stop)
      cat <<'EOF'
ternuxx stop — Stop the recorded native desktop session

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
ternuxx restart — Restart the native desktop session

Runs stop, then start. It changes process and session state, and start options
such as --display N are accepted. See 'ternuxx stop --help' and
'ternuxx start --help' for lifecycle boundaries and requirements.
EOF
      ;;
    status)
      cat <<'EOF'
ternuxx status — Inspect the recorded native desktop session

Reads session state and verifies recorded process identities. It does not
start or stop processes. GUI visibility is reported as unknown because the
Termux:X11 Android app's visible state is not inferred by the CLI.
EOF
      ;;
    checkpoint)
      cat <<'EOF'
ternuxx checkpoint — Prepare or verify reboot continuity evidence

Native Termux only. Records a private checkpoint beneath the configured
Ternuxx state directory. Verification compares boot IDs when available and
records service readiness as not collected until a separate live check runs.
Pending tests are never executed automatically.

  ternuxx checkpoint prepare --test-id <id> [--pending-test <id> ...]
  ternuxx checkpoint verify <checkpoint-id>

This writes private evidence to the native Termux home. It does not configure
boot startup, start services, acquire Wake Lock, or interact with PRoot.
EOF
      ;;
    ssh)
      cat <<'EOF'
ternuxx ssh inspect/start/stop - Native SSH diagnostics and fixed Runit service control

  ternuxx ssh inspect
  ternuxx proot status # Inventory installed guests without entering them
  ternuxx ssh start                         # read-only preview
  ternuxx ssh start --yes --plan-id <id>    # apply exact preview
  ternuxx ssh stop                          # read-only preview
  ternuxx ssh stop --yes --plan-id <id>     # apply exact preview

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
ternuxx proot status — Read-only installed guest inventory
ternuxx proot verify --distro debian (--guest-user USER|--guest-user-from ternux-state) --display :N --backend zink|virgl

`status` lists installed distributions without entering a guest. `verify` enters
the selected Debian guest only to run the identified Ternux guest companion's
version and read-only status checks with the selected display/backend and Ternux
audio endpoint. `--guest-user-from ternux-state` reads only the non-root `user`
key from Ternux's private, Termux-owned state file; the account value is not
returned or logged. It fails closed on unsafe paths or file permissions. The
verifier does not start/stop a desktop, host service, or package operation.
Profile ownership remains unverified; this is diagnostic handoff only, not
general guest command execution.
EOF
      ;;
    reboot)
      cat <<'EOF'
ternuxx reboot — Native reboot-test evidence (no reboot command is provided)

  ternuxx reboot status [test-id]
  ternuxx reboot prepare --test-id <id> --baseline-json <object>
  ternuxx reboot verify <test-id>
  ternuxx reboot resume-info <test-id>

Preparation writes a private, atomic checkpoint and always records
NOT_READY. It does not arm Termux:Boot, start/stop services, or reboot.
Verification compares boot IDs and records evidence; it never resumes tasks.
EOF
      ;;
    boot)
      cat <<'EOF'
ternuxx boot status — Read-only Termux:Boot capability inspection
ternuxx boot profile status
ternuxx boot profile preview <cli-only|native|proot|hybrid>
ternuxx boot gui <on|off> [--yes]
ternuxx boot enable --profile <mode> [--yes]
ternuxx boot disable [--yes]

The default profile is cli-only, so GUI startup after reboot stays off.
Use the direct GUI toggle; it previews by default and --yes applies the plan:
  ternuxx boot gui on
  ternuxx boot gui on --yes
  ternuxx boot gui off
  ternuxx boot gui off --yes
These commands preview first; --yes applies only the shown Ternuxx-owned file
changes and preserves unrelated boot scripts. Native starts Ternuxx-owned
X11/XFCE processes; opening the Android Termux:X11 app and visible GUI remain
separate. Android boot delivery is independently unverified. PRoot and hybrid
profiles remain blocked until their ownership-aware adapter is implemented.
EOF
      ;;
    wakelock)
      cat <<'EOF'
ternuxx wakelock status — Read-only Wake Lock capability inspection

Reports command availability and the ownership limitation. It never invokes
termux-wake-lock or termux-wake-unlock; Android lock-holder state remains
unknown unless a verified platform API is added.

  ternuxx wakelock acquire <owner>
  ternuxx wakelock release <owner>
  ternuxx wakelock acquire native.sshd --persistent

Acquire/release tracks a Ternuxx-owned lease in private native state. Only the
owner process can release its non-persistent lease. Persistent leases are
reserved for the native SSH service and must be released by that service's
manager. Android still exposes one app-global lock; unrelated Termux clients
are outside this coordinator.
EOF
      ;;
    install)
      cat <<'EOF'
ternuxx install — Preview or install the native desktop packages

By default, validates recent official Termux package indexes and prints a
constrained APT simulation. It does not refresh package indexes or change
packages. The plan is limited to the base desktop package set and refuses
removals, upgrades, recommendations, or packages sourced outside the official
Termux repositories.

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
ternuxx check — Inspect device readiness

Reports available commands, package readiness, and Termux:X11 presence. It
does not install packages or intentionally modify files. Device interfaces
queried by diagnostic tools may have their own runtime behavior.
EOF
      ;;
    doctor)
      cat <<'EOF'
ternuxx doctor — Run the available diagnostics

Runs the read-only Doctor report with stable finding IDs, severity, scope, and
suggested actions. Use --json for structured output. Add --graphics to probe the
current DISPLAY; this does not start a desktop/workload, and detection alone
does not prove accelerated execution.
EOF
      ;;
    info)
      cat <<'EOF'
ternuxx info — Show system information

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
      nt_fail "No help available for '$cmd'. Run 'ternuxx help' for usage."
      return 1
      ;;
  esac
}

nt_cmd_help() { nt_help "${1:-}"; }
