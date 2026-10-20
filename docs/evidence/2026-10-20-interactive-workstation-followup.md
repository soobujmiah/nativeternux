# P3 Interactive PRoot workstation follow-up - 2026-10-20

Phase: `P3`

## Repository and preservation
- Native Termux checkout: /data/data/com.termux/files/home/ternuxx; origin identifies soobujmiah/ternuxx.
- Branch main, HEAD 69e378eb33247678437bda4b2de9ab25f6bcb91d.
- Initial dirty worktree: 170 status entries. A local snapshot ref snapshot/2026-10-20-pre-workstation-lifecycle points at starting HEAD. Pre-existing changes were preserved.
- Final worktree: 172 status entries. No commit or push.
- The earlier lifecycle report is historical; its successful TTY login claim does not describe this continuation.

## Ownership and recovery
- The registry initially contained four stopped records; the previously reported unverified marker-failure record was not present. Its exact original cause cannot now be reconstructed.
- Ownership requires process-start identity, private session/group identity, marker, fixed profile signature, and rootfs/launcher device+inode checks. No one signal, PID, command text, or rootfs identity alone authorizes signaling.
- Added read-only proot.sessions.health diagnostics and stricter typed record validation. Recovery distinguishes absence/PID reuse from unreadable or permission-hidden state, live identity mismatch, zombie exit, and session/group mismatch. Reconciliation requires a fresh preview, preserves an audit transition, and never signals or adopts.
- Fixture tests cover marker loss, PID reuse, process-start mismatch, permission-hidden process, group mismatch, malformed and symlinked registry, missing identity, duplicate starts, and health.
- Three disposable TTY login attempts failed closed before exposing a guest shell. On the final attempt process-start, private group, marker, translated login argv, rootfs and launcher checks matched; expected guest cwd and numeric guest UID checks did not. No guest shell input was sent. Each recorded PID was later proven absent, reconciled through a new preview and explicit apply, and marked stopped. No signal was sent.
- Current session list reported all seven managed records stopped. Health for the last failed attempt reports stopped, released ownership, null exit code, and reattach_supported=false.

## Interactive and persistent session qualification
- debian-interactive remains a fixed sbj foreground TTY profile using the installed Debian rootfs. It does not switch users or launch GUI/services.
- Live acceptance did not pass: runtime identity verification rejected all three attempts due to cwd and guest identity evidence mismatch. No interactive shell, startup behavior, job control, or clean shell exit is claimed here.
- tmux, screen, dtach, abduco, and byobu were unavailable in Native Termux PATH. No multiplexer was installed. Foreground attached mode is available in code; reconnect/reattach is unsupported.
- Installed proot-distro source has a login-time hook that can rewrite /etc/profile.d/termux-profile.sh in the Debian rootfs. The file mtime observed after attempts predates them, but no before-hash was captured. A write by those attempts cannot be attributed or ruled out. No manual rootfs changes or restoration were performed. No further live PRoot login or GUI operation was attempted after finding this hook.

## GUI/X11
- PRoot environment had no usable DISPLAY; read-only checks against candidate :0 and :1 failed. Native X11 sockets existed, but no guest connection was established.
- xdpyinfo, xset, xwininfo, xmessage, glxinfo were present in the guest; none was launched as a GUI test. No window, application survival, or GPU acceleration claim is made.
- Existing floating X11 GUI, display/server configuration, graphics acceleration and audio settings were not changed or used as a destructive target. GUI lifecycle remains unqualified.

## Cron, Termux:Boot, legacy workflows
- Cron status: scheduler stopped, no live scheduler process, zero jobs/executions.
- Boot status: Termux:Boot installed/enabled; dedicated 20-ternuxx-cron script missing; scheduler stopped; actual boot delivery unverified.
- No production Cron start/job, boot setting/script modification, or reboot occurred.
- Legacy db, tx db, x.sh, xgo, killx source was not changed. Launch-command regression tests passed; these commands were not invoked.
- SSH 8022 remained inspection-only. No action on 8023, 8765, or unknown listeners.

## Evidence

## Verification
- Focused lifecycle, management authorization/API/catalog, legacy launch-command, Cron scheduler/ledger, and Termux:Boot command: python3 -m unittest tests.test_proot_sessions tests.test_management_service tests.test_management_authorization tests.test_management_sessions tests.test_management_catalog tests.test_launch_commands tests.test_cron_daemon tests.test_cron_scheduler tests.test_cron_execution tests.test_termux_boot_cron -q - 109 passed.
- Full suite: bash scripts/repo_test.sh - 506 passed in 87.789 seconds.
- python3 -m compileall -q lib tests - passed.
- bash -n lib/management.sh - passed.
- python3 -m json.tool schemas/proot-session-registry.schema.json - passed.
- git diff --check - passed.
- python3 -m tools.repo_knowledge verify - 0 findings.

## Gates and remaining work
- Gate A: current absent-PID reconciliation and fixture behavior verified. Historical marker failure cause unknown because record absent.
- Gate B: not passed; current identity verification fails closed. Resolve proot-distro cwd/guest identity contract without weakening checks or modifying rootfs before a new live attempt.
- Gate C: prior headless lifecycle live-qualified; interactive supervision not. Foreground only; no reattachment.
- Gate D: not passed; no guest X connection/window test.
- Gate E: requested fixtures and full suite passed; production Cron/boot untouched.
- Gate F: health API and limits documented; general workstation and GUI lifecycle unqualified.
- P3 remains in progress; P4 remains incomplete/unqualified.
