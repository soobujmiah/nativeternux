# Ternuxx-owned Debian PRoot sessions

**Status (2026-10-20):** fixed profile inventory, exact-session ownership controls, foreground TTY login path, bounded health reads, and safe stale-record reconciliation are implemented. Disposable headless lifecycle is live-qualified. Current TTY login qualification failed closed because the runtime identity signature did not match the expected guest cwd/UID evidence. GUI supervision, detach/reattach, guest service management and PRoot boot launch remain unqualified.

## Rootfs and legacy integration

The current Native Termux proot-distro installation discovers the Debian guest at $PREFIX/var/lib/proot-distro/containers/debian/rootfs. Discovery checks the absolute configured path, rejects a symlinked rootfs or launcher, and records device/inode identity. It does not modify the rootfs.

The existing db alias remains proot-distro login debian --shared-tmp --user sbj. The debian-interactive profile uses that login selection and runs /usr/bin/env TERNUXX_PROOT_SESSION=<random-id> /bin/bash --login as the explicit guest command on a private controlling PTY. It requires a real caller terminal, relays terminal input/output and size changes, supports shell job control, and remains attached until the guest shell/session exits. Exit status is persisted in schema v3. It does not create a detached terminal multiplexer, start a GUI, start a service, modify shell startup files, or alter Termux:Boot. Its default guest working directory is left to proot-distro/Debian login behavior.

isolated-probe remains a bounded headless session using proot-distro login --minimal debian and a fixed /bin/sleep target. It redirects stdio to /dev/null; it is a diagnostic profile, not a workstation.

## Ownership and persistence

The private registry at $TERNUXX_STATE_DIR/proot/sessions.json is version 3, mode 0600, and atomically replaced under an OS file lock. Version 1 and 2 records are read and upgraded in memory, then written as version 3 on the next mutation. A record holds a stable session ID, profile/version/mode, rootfs and launcher device/inode identity, a random marker, expected fixed argv, PID, kernel process-start ticks, session/process-group identity, timestamps and bounded transition history. It stores no shell environment values or secrets.

A live session is considered Ternuxx-owned only when PID and process-start identity match, PID is the recorded session/process-group leader, the private marker is visible, the profile signature matches the actual translated proot argv and (for the interactive profile) its cwd and numeric guest identity match the selected rootfs, and the rootfs/launcher inode identities still match. proot-distro rewrites public distro/user arguments, so verification uses the actual proot command, guest rootfs cwd, passwd UID/GID, fixed login argv and random marker rather than searching for the removed public --user/debian tokens. The marker is passed as a guest env argument because proot-distro does not preserve the host marker in the resulting PRoot process environment. PID, command text, process group, or rootfs identity alone is insufficient.

Unmanaged PRoot sessions are only reported by the read-only inventory and are never adopted. A persisted running record with no matching process is presented as unverified while retaining its recorded_state; reads do not rewrite or delete it. Stop uses a fresh preview plan, revalidates process identity and filesystem identities immediately before signaling, and sends SIGTERM only to the exact newly created Ternuxx session group. It waits boundedly and never sends a force signal. If identity is unclear, it refuses.

A crash after starting a child can leave an unverified registry entry. tx mng proot recover SESSION_ID is read-only. tx mng proot reconcile SESSION_ID previews an explicit registry update; applying its exact plan marks the old record stopped only when /proc proves the PID absent, replaced, or exited. It never signals the current PID, adopts a process, or removes the audit record. Live-but-unverified records remain untouched. A completed interactive shell is marked stopped by its supervising tx command when it returns. If the parent is killed unexpectedly, the process is not automatically reclaimed.

## Supported interface

- tx mng proot profiles list|show
- tx mng proot sessions list|show|health SESSION_ID
- tx mng proot start --profile ID prints a plan by default.
- Repeat with --yes --plan-id ID to apply the selected plan.
- tx mng proot stop SESSION_ID prints a plan; repeat with --yes --plan-id ID to stop only that session.
- tx mng proot reconcile SESSION_ID previews safe exit reconciliation; apply only with --yes --plan-id ID.

Profiles are fixed and typed; user-supplied shell strings are not accepted. The isolated probe and interactive login build launch environments without any LD_* variables, preventing inherited host loader overrides from reaching the native launcher or guest. debian-interactive is a synchronous foreground terminal login, so it is not offered by Web UI or background callers. Browser mutation scopes do not include proot.session.manage. TUI, Web and GTK remain read-only for PRoot lifecycle in this increment.

## Qualification limits

The headless profile has a live disposable start/stop proof. In this continuation, three TTY-bound login attempts failed before a guest shell was exposed: PRoot process-start, private group, marker, translated login argv, rootfs and launcher evidence matched, while the expected guest cwd and numeric guest identity checks did not. No shell input was sent. Each recorded PID was later proven absent, then reconciled through a fresh preview; no signal was sent. The earlier evidence report successful TTY-login claim is historical and does not qualify the current code. Non-TTY calls fail closed. A bounded health read reports identity status, exit evidence and attachment as unavailable; no multiplexer is installed, so detach/reconnect remains unsupported. The existing floating X11 session was left untouched. The inspected PRoot environment had no usable DISPLAY and candidate :0/:1 checks could not connect; this does not qualify X11 connectivity, window creation, app survival or GPU acceleration. Installed proot-distro source includes a login-time hook that can write /etc/profile.d/termux-profile.sh into the guest rootfs. The file mtime observed after our attempts predated them, but no before-hash exists; attribution cannot be established, so no more live logins or rootfs operations were attempted. Legacy db, tx db, x.sh, xgo and killx were not modified or invoked.


## Native-owned workstation handoff (2026-10-20)

Ternuxx Native Termux is the authority for its host display/audio lifecycle and Debian handoff. Default guest identity resolution reads the installed Debian rootfs etc/passwd and accepts one ordinary non-root account with home /home/NAME; no Ternux executable or state file is required. Ambiguous accounts require an explicit --user.

For Native tx db, managed interactive PRoot sessions, app launch, and bounded verification, Ternuxx passes the active DISPLAY (default :1), Debian Zink/Turnip variables, and a validated Native PulseAudio cookie through one bind to /tmp/.ternuxx-pulse-cookie. Zink passes /dev/kgsl-3d0 as /dev/kgsl and the available /dev/dri tree. These are host capabilities with guest ABI-compatible Mesa userspace; Native Bionic libraries are never copied into Debian. VirGL remains an optional route, not the active default. CPU remains the baseline. NPU is experimental and unqualified.

The installed proot-distro login implementation writes /etc/profile.d/termux-profile.sh from the environment supplied to each normal guest login. This is its login-shell persistence mechanism, not a Ternux CLI dependency. Leave that package-generated file and its writer intact. Ternuxx writes the same Zink/display/audio baseline for each Debian login and applies selected backend variables after the shared profile has loaded, to the launched process only. Thus a VirGL shell does not change what a parallel or later default Zink login inherits; a su - from that VirGL shell returns to the stable Zink baseline. Keep unrelated sudoers and guest profile hooks untouched. A separate explicit Ternux session adapter remains optional; normal Ternuxx operation does not query it.
