# Managed SSH automatic-start policy — 2026-10-22

Phase: `P4`

Gate: IN PROGRESS

## Change

- Added `ssh.service.autostart.status`, `.preview`, and `.apply` in the shared Native management service.
- The only target is the validated `$PREFIX/var/service/ternuxx-sshd/down` marker. Enable means remove that empty marker; disable means create it with mode 0600. The source validates the Native Termux prefix, exact owned service directory and `run` file, state directory, current marker type/owner/size, exact preview identity, exclusive create, directory identity and file identity.
- This setting changes only what Runit does at its next supervisor start. It does not start or stop the current process. Live start/stop/restart remain separate, individually preview-confirmed service actions. This matches the installed Termux service contract: disabled services have a `down` file; the runit supervisor does not start a service immediately when that marker exists. See [Termux services](https://github.com/termux/termux-services) and [runsv manual](https://www.smarden.org/runit/runsv.8).
- CLI, TUI, authenticated Web, GTK and the management catalog expose the preference through the shared typed operation. GTK was rebuilt and installed; final Native SHA-256 recheck matched source C, bridge, binary, launcher, and desktop entry to management-center.identity. Desktop entry remains in `$PREFIX/share/applications/ternuxx-management-center.desktop`.

## Evidence

## Verification

- Focused tests: **125 passed** across autostart filesystem safety, management service, authorization/session/Web scope, desktop bridge and SSH client contract.
- Full Native suite: `bash scripts/repo_test.sh` — **815/815 passed** in 125.500 seconds.
- CLI help contract and `py_compile` passed; `git diff --check` passed before the full suite.
- Native read-only status reported automatic start enabled (no `down` marker). A preview to disable it returned the exact change plan. Before/after `sv status` remained identical (`ternuxx-sshd` PID 21035) and the `down` marker remained absent. No preference was applied and the service was not signalled.
- Installed GTK source, bridge, binary, launcher and desktop entry hashes match the install identity. GTK `--self-check` was already confirmed on the rebuilt app; visual interaction remains unreviewed.

## Remaining

Wake Lock policy per service, native cold-boot delivery/verification, disposable SSH authentication/recovery, durable credential rollback, and user-operated visual review remain open. P4 stays in progress.
