# P3 TUI attached interactive PRoot login follow-up — 2026-10-21

Phase: `P3`

I continued the Native Termux checkout at `main`, HEAD `dfa3f63dec45afccd9de06b3ff9d0652b325c2b8`. The worktree already contained uncommitted TUI and TUI-test changes for a `debian-interactive` attached-login action; I preserved those changes.

The TUI route uses the shared typed service, previews the fixed `debian-interactive` profile, checks its profile, foreground-TTY mode, and exact plan-ID shape, asks for explicit confirmation, then restores the terminal before invoking the attached login. I added a visible warning that the TUI route is not live-qualified. Focused tests cover preview confirmation, terminal handoff, and rejection of an invalid preview.

I inspected all seven saved interactive-session records using the read-only `tx mng proot recover` operation. Four records are historical failed starts: two retain explicit `cwd_rootfs=false` and `guest_ids=false`; another has no readable process evidence; one retains only a failed profile signature. Three other records reached verified login states; two specifically reached `login-pty-verified` and exited with code 0. The session inventory currently reports all nine managed records stopped (two probes and seven interactive records). Therefore the Native CLI attached-login path has a successful historical qualification as well as failed attempts; it is inaccurate to say every or the latest attempt failed.

The owner clarified that the currently running Codex PRoot Debian shell was entered through the legacy `tx db` path. That live shell is separate from the saved Ternuxx-managed session records and was not inspected, signaled, or changed. Its successful launch does not by itself qualify the new TUI route.

I inspected the installed Native `proot-distro` login source. It builds `--change-id=<UID>:<GID>`, defaults the guest working directory to the selected user's home, and changes the host process directory to the pinned rootfs before executing PRoot. Historical failures show the runtime checks disagreed with the expected cwd and guest IDs, while a later managed CLI start passed verification. The cause of the differing outcomes is not established; I did not weaken checks.

Verification: `python3 -m unittest tests.test_terminal_ui -q` passed (30 tests). One expected noninteractive test emitted `tx tui needs an interactive terminal.` This is source review, focused test, and read-only registry review. I did not start an interactive PRoot login, inspect or modify the active Codex guest, start or stop services, reboot, commit, or push. The current TUI route remains live-unqualified. P3 listener attribution and cold-boot delivery also remain open.

## Evidence

Source review: `lib/terminal_ui.py`, `tests/test_terminal_ui.py`, `lib/proot_sessions.py`, and the installed Native `proot-distro` login source. Repository status and latest P3 evidence were read from the Native Termux checkout.

## Next action

The shared-service call path and focused TUI tests are reviewed; the tests pass. Keep TUI live acceptance deferred because proot-distro login can write package-owned guest profile state. Continue the independent P3 listener-attribution and cold-boot gates; do not advance to P4 until the P3 exit gate passes.
