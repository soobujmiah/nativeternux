# P3 interactive PRoot TTY relay fixture audit — 2026-10-20

Phase: `P3`

## Scope
Worked in the Native Termux checkout through SSH 8022. Extracted the foreground terminal relay from `login_interactive` into a private helper so its actual fd relay and cleanup behavior can be fixture-tested. No live PRoot login, desktop restart, guest write, or rootfs operation was performed.

## Changes
- `_relay_interactive_pty` owns input/output relay, SIGWINCH size propagation, child exit polling, and terminal/master-fd cleanup.
- Terminal attributes are restored and the master fd closed after normal relay completion, relay exceptions, and an initial terminal-probe failure.
- Added fixture coverage for input bytes to the child PTY, child output to caller output, terminal-size ioctl propagation, exit status, terminal restoration, and fd cleanup.
- Added exception-path coverage for restoration and early terminal-probe failure.
- Attach/reconnect remains unsupported. This fixture verifies foreground relay mechanics; it does not launch the installed Debian guest or resolve prior live cwd/guest-ID mismatch.

## Evidence
- `python3 -m unittest tests.test_proot_sessions -q`: 34 tests passed on Native Termux.
- `bash scripts/repo_test.sh`: 622 tests passed on Native Termux.
- `git diff --check`: passed.
- Existing Native XFCE and Debian GUI sessions were not stopped or restarted.

## Next P3 gate
The TTY ownership fixture contract is covered. Continue the shared-client action parity gate: the shared API/CLI supports Cron job create/update/remove, while TUI and GTK have no mutation action and Web deliberately omits `cron.manage`. Add a preview/explicit-confirm/apply contract before exposing these operations across all clients. Keep the live interactive PRoot mismatch documented for P4 guest qualification; do not attempt another login in the current guest.
