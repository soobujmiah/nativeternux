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
  tx db              Open the Debian PRoot shell (default backend: Zink)
  tx pgui            Open Debian XFCE standalone :0 or nested in Native :1
  tx gui             Open the Native Termux GTK management center
  tx start           Start the native Termux:X11/XFCE desktop
  tx tui             Interactive terminal management
  tx web             Open the shared Web UI in a selected browser
  tx terminal        Run or connect to the optional shared PRoot terminal broker

Commands by task:
  Desktop:       start, stop, restart, status, gui, tui, web
  Debian PRoot:  db, pgui, proot, app, audio, virgl, terminal
  Graphics:      graphics, info, check, doctor
  Management:    mng (catalog, app shortcuts, Cron, timezone, graphics,
                 PRoot sessions, boot, GTK center, HTTP service)
  Access:        ssh, remote
  Recovery:      checkpoint, reboot, boot, wakelock, backup, recovery, restore
  Setup:         install
  Reference:     guides, help

Use `tx help NAME` or `tx NAME --help` for command options and safety rules.
Common short forms: up=start, dn=stop, rs=restart, st=status, ck=check,
inf=info, doc=doctor, mg=mng, pr=proot, cp=checkpoint, ra=remote, rb=reboot,
bt=boot, wl=wakelock, in=install, bk=backup, rc=recovery, rt=restore,
g=guides, h=help. `management` is a deprecated spelling of `mng`.

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
  tx pgui
  tx pgui status
  tx backup list
  tx recovery status
  tx recovery resolve OPERATION_ID
  tx remote access preview
  tx proot verify --distro debian --guest-user-from rootfs --display :1 --backend zink

Safety:
  start/stop/restart change process and session state. install --yes requires
  an exact preview plan ID. Recovery apply operations require their preview ID.
  Remote access defaults to disabled and never enables public ingress.

`app` launches a Debian app entry; `mng papps sync` refreshes the Native XFCE
PRoot Apps menu from installed guest applications. Use `tx help mng` and
`tx help app` for detailed options.
EOF
      ;;
    terminal)
      cat <<'EOF'
tx terminal serve — Run the Native Termux terminal broker in the foreground
tx terminal service status|preview-install|install — Manage its previewed Runit service
tx terminal status — Read the optional broker status
tx terminal start — Preview, confirm, and attach to the fixed Debian login
tx terminal attach SESSION_ID — Attach to one Ternuxx-owned session
tx terminal close SESSION_ID — Preview and confirm exact-session stop

Start the broker in a Native Termux terminal before connecting clients. The
broker accepts only the fixed debian-interactive profile, private Unix socket,
same-UID peer, bounded terminal bytes, and exact preview-bound session actions.
The attach key Ctrl-] detaches the client without closing the guest. Broker
shutdown closes its PTY and records unknown state; it never signals the guest.
PRoot remains optional and no current guest is adopted by this command.
EOF
      ;;

    db)
      cat <<'EOF'
tx db [--user NAME|--root] [--distro NAME] [--display :N] [--backend zink|virgl] [-- COMMAND...]

`tx db` is Ternuxx’s first-party command, distinct from a bare `db` shell alias.
A bare `db` or `droot` alias may call `proot-distro` directly and bypass Ternuxx’s
validated display/audio/environment handoff. Use `tx db` for the managed path.

Runs from Native Termux. Debian Zink/Turnip is the default and remains unchanged.
Use --backend virgl to ensure Ternuxx's Native virgl_test_server_android is ready,
then pass only the VirGL client environment and display/audio handoff to Debian.
The VirGL service persists after the shell exits because other guest workloads may
still use it; inspect with `tx virgl status` and stop only when no client is attached.
CPU execution is independent of the graphics backend. NPU execution is not wired.
EOF
      ;;
    graphics)
      cat <<'EOF'
tx graphics native status|enable --prefix PATH|disable

Select an extracted Native KGSL Mesa candidate for future desktop sessions.
Enable validates the required candidate files and saves its prefix in the
private Ternuxx state directory. Restart the desktop to apply it to XFCE and
new native applications. Disable returns future sessions to the system stack.
The candidate remains local and experimental; GPU inference is not implied.
EOF
      ;;
    virgl)
      cat <<'EOF'
tx virgl [status|start|stop] [--display :N]

Manage the Ternuxx-owned Native VirGL vtest server used by Debian PRoot clients.
Start is identity-checked and uses a private Unix socket. Stop acts only on the
recorded Ternuxx server and refuses when socket clients or ownership are unclear.
The server requires the optional `virglrenderer-android` Native package. This
command never changes the Debian rootfs or the existing Zink/Turnip userspace.
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
tx mng logs list|read SOURCE_ID  Read bounded Ternuxx-owned log tails
tx mng proot status — Inspect installed guest and Ternuxx session ownership
tx mng proot profiles list|show — Inspect validated headless and interactive profiles
tx mng proot sessions list|show|health — Inspect owned sessions, liveness, exit and attachment capability
tx mng proot start --profile ID — Preview a start; repeat with --yes --plan-id ID to confirm
tx mng proot stop SESSION_ID — Preview exact-session stop; repeat with --yes --plan-id ID to confirm
The debian-interactive profile requires a TTY and opens a foreground login shell; it does not start GUI or services.
tx mng hermes status — Inspect optional Hermes scheduler (read-only)
tx mng cron status/start/stop — Inspect or explicitly manage the lease-guarded scheduler
tx mng cron jobs list|show|validate|next-runs|create|update|enable|disable|remove|apply — Preview job changes; apply exact plan with --yes --plan-id
tx mng cron executions list|show — Read saved execution history (does not run jobs)
tx mng boot helpers status — Check only the two repository-owned service/recovery scripts
tx mng boot helpers preview deploy HELPER — Show exact hashes before replacement
tx mng boot helpers apply deploy HELPER --yes --plan-id ID — Deploy with a private rollback snapshot
tx mng boot helpers preview rollback HELPER SNAPSHOT_ID — Preview exact restoration
tx mng boot helpers apply rollback HELPER SNAPSHOT_ID --yes --plan-id ID — Restore saved helper
tx mng boot cron status|validate — Inspect the opt-in official Termux:Boot Cron entry
tx mng boot cron preview {enable|disable} — Preview exact script changes
tx mng boot cron enable|disable --yes --plan-id ID — Apply the reviewed boot-script plan
tx mng timezone status|list — Inspect configured timezone and available IANA zones
tx mng timezone set IANA_NAME — Persist an explicitly selected timezone
tx mng graphics status PROVIDER | verify PROVIDER API [:N] | select native BACKEND
tx mng doctor [--graphics] — Run read-only Doctor via the shared service
tx mng app launch APP_ID — Launch a named PRoot app on native X11
tx mng shortcuts list — View PRoot app launchers
tx mng shortcuts plan {add|remove} APP_ID — Preview a launcher change
tx mng shortcuts apply {add|remove} APP_ID --plan-id ID --yes — Confirm the exact preview
tx mng http serve — Run the authenticated loopback management API in foreground
tx web — Open the browser UI over the same shared service

The Web UI binds only to 127.0.0.1 (default port 8765), copies the one-time
bootstrap secret to the Termux clipboard, opens the local browser, and runs until Ctrl-C. The secret is not saved. If clipboard copy fails,
the server stops without revealing it; use --show-secret-on-clipboard-failure
for the explicit private-terminal fallback. Browser access uses the shared
management service with scoped reads and narrow confirmed actions: Native
desktop lifecycle, graphics status/verification and Native backend selection,
GUI Activity-monitoring policy, managed SSH 8023 start/stop/restart, named PRoot app
launch with per-app confirmation, previewed single PRoot shortcut changes, and
Cron status/job/history reads, PRoot session/recovery reads, and preview-confirmed
fixed 300-second isolated probes with exact verified-owned stop. Browser clients
cannot start interactive PRoot login sessions or reconcile recovery records. Boot
changes, backup/restore, timezone mutation, Cron job mutation, and other recovery
writes remain outside the Web session.
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
    pgui)
      cat <<'EOF'
tx pgui [start [--mode auto|standalone|nested]|status|stop]

Starts the existing Debian XFCE desktop. Auto starts standalone on Termux:X11
:0 when Native GUI is stopped; when Native GUI is running on :1, it starts a
full nested desktop through Debian Xephyr :2. Standalone and Native desktops
are mutually exclusive. Nested mode shares Native :1 as the host display and
uses isolated Debian Zink/Turnip plus the authenticated Native PulseAudio
endpoint. Ctrl-C in the launching terminal closes only the nested desktop.
`tx pgui stop` stops only a verified Ternuxx-owned standalone :0 session.
Individual Debian apps remain available through `tx mng app launch` shortcuts.
EOF
      ;;
    terminal)
      cat <<'EOF'
tx terminal serve — Run the Native Termux terminal broker in the foreground
tx terminal service status|preview-install|install — Manage its previewed Runit service
tx terminal status — Read the optional broker status
tx terminal start — Preview, confirm, and attach to the fixed Debian login
tx terminal attach SESSION_ID — Attach to one Ternuxx-owned session
tx terminal close SESSION_ID — Preview and confirm exact-session stop

Start the broker in a Native Termux terminal before connecting clients. The
broker accepts only the fixed debian-interactive profile, private Unix socket,
same-UID peer, bounded terminal bytes, and exact preview-bound session actions.
The attach key Ctrl-] detaches the client without closing the guest. Broker
shutdown closes its PTY and records unknown state; it never signals the guest.
PRoot remains optional and no current guest is adopted by this command.
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

`tx db` is Ternuxx’s first-party command, not the bare `db` shell alias. A bare
`db` or `droot` alias may call `proot-distro` directly and bypass Ternuxx’s
validated display/audio/environment handoff. Use `tx db` for the managed path.

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
and offers Android, installed Native Termux, installed Debian PRoot, or auto-select.
If neither clipboard nor browser-form handoff works, the server stops without
revealing the code. Use --show-secret-on-clipboard-failure for an explicit
private terminal fallback. Native/PRoot X11 browsers receive the code in the login field; Android uses clipboard paste.
Choose with --browser android|native|proot|auto to skip the prompt.
Auto-select prefers an installed Native browser, then Debian PRoot Firefox ESR,
then Android's default browser. Press Ctrl-C to stop. The Web client uses
the shared management API
with scoped reads, confirmed native desktop lifecycle, graphics verification and
Native backend selection, monitoring-policy configuration, managed SSH 8023
preview/confirmation, named PRoot app launch, single shortcut changes, and Cron
status/job-list/history, PRoot session/recovery reads, preview-confirmed isolated
probes, and the shared broker-backed Debian terminal. Terminal start and close
require a fresh exact plan; attach uses a short-lived, single-use channel. Boot
changes, backup/restore, timezone mutation, Cron job mutation, and recovery
reconciliation remain CLI-only.
EOF
      ;;
    tui)
      cat <<'EOF'
tx tui — Interactive terminal client

The TUI reads the shared resource catalog and uses the shared typed service.
Use ←/→ (or h/l) to change categories, ↑/↓ (or j/k) to select a resource,
Enter to inspect live status, / to search, a to run an action offered for that
resource, H for operation history, v for the last operation details, r to reload
the catalog, and q to exit. Actions include confirmed desktop and managed SSH
8023 lifecycle, Native graphics selection and graphics verification, monitoring
policy, named PRoot app launch, and Cron job listing. Other operations remain
available through their documented CLI commands; catalog support is not shown
as an implemented guided action when this TUI has no action flow.
EOF
      ;;
    gui)
      cat <<'EOF'
tx gui — Native Termux GTK management center

  tx gui                              Open the installed GTK management center
  tx gui start|stop|restart|status    Preserve native desktop lifecycle aliases
  tx gui monitor status|enable|disable|configure OPTIONS
  tx gui monitor service status|preview-install
  tx gui monitor service install --yes --plan-id PLAN_ID

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
tx ssh inspect/keys-list/enroll-preview/enroll/revoke-preview/revoke/client-key-preview/client-key-create/autostart-status/autostart-preview/autostart-apply/start/stop/restart - Native SSH management

  tx ssh inspect
  tx ssh keys-list                    # shared Termux account key fingerprints and labels
  tx ssh client-key-preview --key-name recovery8023
  tx ssh client-key-create --key-name recovery8023 --yes --plan-id <id>
  tx ssh autostart-status
  tx ssh autostart-preview --autostart-disabled
  tx ssh autostart-apply --autostart-disabled --yes --plan-id <id> # current sshd keeps running; next supervisor start stays down
  cat ~/.ssh/id_ed25519.pub | tx ssh enroll-preview --public-key-stdin
  cat ~/.ssh/id_ed25519.pub | tx ssh enroll --public-key-stdin --yes --plan-id <id>
  tx ssh revoke-preview --key-fingerprint SHA256:<fingerprint>
  tx ssh revoke --key-fingerprint SHA256:<fingerprint> --yes --plan-id <id>
  # Enrollment/revocation affects the shared Termux account: SSH 8022 and 8023.
  tx proot status # Inventory installed guests without entering them
  tx ssh start                         # read-only preview
  tx ssh start --yes --plan-id <id>    # apply exact preview
  tx ssh stop                          # read-only preview
  tx ssh stop --yes --plan-id <id>     # apply exact preview
  tx ssh restart                       # preview; warns that 8023 clients may disconnect
  tx ssh restart --yes --plan-id <id>  # apply exact preview

Reports whether OpenSSH/configuration is present, whether sshd accepts the
current config, allowlisted effective authentication/bind policy, observed
TCP listeners and whether procfs permitted reading them, process presence,
Termux:Boot directory presence, and whether a runit command is available. It
inspect does not read key or password files, display raw config, or test authenticated
connectivity. keys-list reads only the fixed native authorized_keys file and returns key
type, fingerprint, and sanitized comment; it never returns key bytes. Start/stop preview and apply control only the fixed Ternuxx
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
tx proot setup status
tx proot setup adopt-preview --user NAME
tx proot setup adopt --user NAME --yes --plan-id PLAN_ID
tx proot setup fresh-preview --user NAME [--alias ternuxx-replay-NAME]
tx proot setup fresh-install --user NAME [--alias ternuxx-replay-NAME] --yes --plan-id PLAN_ID
tx proot legacy-cli preview
tx proot legacy-cli remove --plan-id PLAN_ID
tx proot legacy-cli rollback --backup-id BACKUP_ID
tx proot legacy-cli host preview
tx proot legacy-cli host remove --plan-id PLAN_ID
tx proot legacy-cli host rollback --backup-id BACKUP_ID

--backend is the expected renderer class for this read-only probe; it does not switch drivers.

gui start currently fails closed because a full Debian desktop must be nested
inside the native Termux :1 desktop; it must not open a separate :0 Activity.
Specific GUI apps remain available through tx mng app launch APP_ID. No guest
reinstall or rootfs replacement is part of this route. Status lists installed
distributions. Verify enters Debian only to run a fixed Ternuxx read-only
display/audio/renderer probe. The rootfs source resolves the unique ordinary
non-root account from Debian passwd; unsafe paths or ambiguous accounts fail
closed. The old Debian guest and Native Ternux CLI command files were retired after exact hash-bound previews. Their private snapshots were later purged at the owner's request; rollback is no longer available for those retired files. No PRoot signal or rootfs replacement occurred. The Ternuxx replacement is `tx proot verify` and the shared guest diagnostics. A prior-name recovery compatibility path was retained at that checkpoint. The Ternuxx-owned setup profile and read-only adoption record are managed with
tx proot setup. Adoption writes only a private Native Ternuxx state record; it
does not change guest files, packages, services, or desktop lifecycle. Fresh provisioning creates the default `debian` alias only when it is absent and never
changes the existing `debian` rootfs. Preview lists package groups, image tag,
space available, and exact plan ID. Apply creates the new alias, installs the
manifest package groups, locale, and user, then records installed package
version evidence. The Debian image tag and APT versions are resolved at apply
time; byte-identical rebuilds are not promised. Turnip rendering remains a
separate verification gate. This route does not invoke the separate Ternux CLI.
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
