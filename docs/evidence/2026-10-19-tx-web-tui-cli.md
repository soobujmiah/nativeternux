# Ternuxx CLI, Web UI, and TUI continuation — 2026-10-19

## Changes

- The public command prefix is `tx`; help shows full command names and keeps short spellings as accepted aliases.
- `tx db` uses the existing Ternux guest-user resolver and `proot-distro login`; no guest reinstall or rootfs replacement was performed.
- The managed Termux shell block retains `gui()` and removes `tdb()`. Existing `db` and `droot` aliases were preserved.
- `tx web` starts the authenticated loopback-only management service, opens the Android browser with `termux-open-url`, and serves a local read-only UI. Browser sign-in exchanges the one-time terminal secret for a session; no credentials are persisted.
- `tx tui` displays shared-service views and provides an operation runner restricted to `management_service.OPERATIONS`. It takes JSON arguments and asks for explicit confirmation for operations in the shared mutation registry. Curses redraws after terminal resize, wraps to the current width, and supports scrolling.

## Verification

- Native Termux `tx db -- printf 'managed-db-ok\n'` completed inside the existing Debian guest.
- `tx web` opened the browser at loopback; the foreground server stopped on Ctrl-C.
- Local loopback checks returned HTTP 200 for the UI and health routes; authenticated `management.catalog` returned success.
- Focused tests passed: 22/22. `tests/test_cli_help.sh` passed; the full repository suite passed 342/342 in 67.458 seconds. A pseudo-terminal resize from 24×80 to 10×35 and back exited cleanly; TUI resize/wrap/scroll tests passed. Bash/Python syntax checks and `git diff --check` passed.
- Native `.bashrc` preview/apply was bound to an exact plan ID. `gui` remained a function, `db` remained the existing PRoot alias, and `tdb` was absent after reload.

## Limits

The browser UI is read-only. TUI operations use the shared service but must still be driven through each operation's typed arguments and its preview/confirmation contract. Graphical UI management and full project phase acceptance remain incomplete. No reboot, commit, or push was performed.
