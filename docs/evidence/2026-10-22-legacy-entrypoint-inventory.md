# Native legacy PRoot entrypoint inventory — 2026-10-22

Runtime: Android aarch64 Native Termux, repository command run through the owner-provisioned SSH 8022 development shell.

## Read-only findings

- The current Native shell startup file defines `db`, `droot`, `x`, `xgo`, and `killx`; no startup file was edited.
- `db` and `droot` call `proot-distro login debian` directly. They do not call the Ternuxx shared management operation or receive its explicit display/audio/provider handoff.
- `x` and `xgo` call `~/x.sh`. The current file is a 112-byte mode-0700 executable wrapper to the checked-in `scripts/proot-x11-app.sh`; the wrapper was read but not executed.
- `scripts/proot-x11-app.sh` requires the already-running Ternuxx display, validates guest X11 reachability, requests the Ternuxx Native audio service, and launches a guest app. It does not call the separate Ternux CLI, start an Android Activity, or stop either desktop session.
- `killx` prints a window-close hint and does not signal processes.
- `./tx db --help` exposes user/root selection, optional installed distro, display/backend, and command arguments. Its Ternuxx command path dispatches to `nt_cmd_db`; it remains the canonical managed path.
- Relevant checked Debian user/root startup files contained no matching `db`, `droot`, `xgo`, or `killx` alias definitions. No guest login was started for this inspection.

## Decision and limits

`tx db` is a Ternuxx first-party command and must not be conflated with the bare `db` alias. Legacy aliases and launchers are not mandatory Ternuxx compatibility requirements. The current `x`/`xgo` path is still a useful Ternuxx-owned app-launch convenience, while `db`/`droot` remain external direct-login aliases; no retirement is justified solely by their names. Ternuxx has no product dependency on those aliases, and they must not be invoked as hidden provider routes.

No shell configuration, launcher, SSH service, rootfs, guest package, or active PRoot process was changed or stopped. No old entrypoint was executed during this inventory. Any future retirement needs exact target ownership, caller/dependency review, proven replacement, preview, backup, and rollback.
