# Native SSH client key generation — 2026-10-22

Phase: `P4`

Status: **Source and Native GTK deployment verified; live key creation/enrollment and visual interaction not performed.**

## Implementation

- Added preview/apply `ssh.client-key.create.*` operations in the shared management service. They create a new Ed25519 client key only under Native `$HOME/.ssh/ternuxx-keys/`, do not overwrite existing destinations, validate the exact preview under a private lock, keep the private key mode 0600, and return no private bytes. The generated key is unencrypted; this limitation is disclosed in the interfaces.
- CLI, guided TUI, authenticated Web, and GTK now expose recovery-key creation. Each route previews then confirms the exact create plan. Creation does not enroll the public key; enrollment remains a separate preview/confirm action whose impact is the shared account on ports 8022 and 8023.
- GTK adds a recovery-key name form and explicit review dialog, validates the bridge response against the exact plan and expected public path, and hands off to the shared typed service. The app-menu launcher remains `Ternuxx Management Center`.
- Added fixture tests for file permissions, destination/path safety, stale previews, no-overwrite behavior, cleanup, shared-service dispatch, malformed plans, catalog/authorization/client contracts.

## Verification

- Focused Native suite: **85 tests passed** across desktop bridge, SSH key generation, management service, and client contract modules. Additional focused rerun after GTK path/name validation: **41 tests passed** across bridge and key-manager modules.
- Native full suite: `bash scripts/repo_test.sh` — **804/804 passed** in 100.109 seconds.
- `bash tests/test_cli_help.sh` and `git diff --check` passed.
- `bash scripts/install-management-center.sh` compiled and installed the GTK binary, launcher, and desktop entry under Native Termux. Installed source/bridge/binary/launcher/desktop hashes match the install identity record; GTK `--self-check` reports GTK 4.24.1 and VTE 0.84.1. Exact current hashes are in the installed identity at `$PREFIX/libexec/ternuxx/management-center.identity` (not copied here because install identity is the live authority).
- Web page was not interacted with in a browser for this key-creation increment; GTK was built/installed but its visual flow was not opened/reviewed. No keypair was generated, no authorized key changed, and no live SSH auth test was run.

## Remaining

Qualify GTK through owner-operated visual review and a disposable credential path; test enrollment/authentication without changing the existing shared authorized-key file. Add durable key-change rollback/recovery, password policy/recovery decision, per-service boot/Wake Lock controls, and cold-boot/auth continuity evidence. P4 remains in progress.

## Evidence

- Source and tests: `lib/ssh_client_keys.py`, `tests/test_ssh_client_keys.py`, `lib/management_service.py`, `lib/terminal_ui.py`, `lib/management_web_ui.html`, `scripts/management_desktop_bridge.py`, and `apps/management-center/management-center.c`.
- Native full suite: 804/804; focused bridge/key/service/client suites: 85/85, plus 41/41 after the final GTK path/name validation rebuild.
- Installed identity: `$PREFIX/libexec/ternuxx/management-center.identity` records matching hashes for the current GTK source, bridge, binary, launcher and desktop entry.
