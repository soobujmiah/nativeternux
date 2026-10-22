# P4 shortcut sync rollback

Date: 2026-10-22
Repository checkout: Native Termux $HOME/ternuxx through SSH 8022
Starting commit: d30594111506d399dd0269c936ed85508695b118

## Implemented

- Bulk shortcut sync now writes a private, versioned rollback record before changing launcher/menu files.
- The record captures exact prior bytes, mode, before hash, expected after hash, plan ID, and status. Records are bounded by entry and byte limits and stored under the private Ternuxx state directory.
- Apply is serialized by a private lock, rechecks the exact plan under the lock, verifies resulting content, and restores captured pre-state on a failed/inconsistent write.
- Added shared management list, preview, and apply operations. Apply requires the rollback ID, exact preview plan, and explicit confirmation.
- Added CLI tx mng papps rollback list and interactive tx mng papps rollback apply ROLLBACK_ID.
- Added an authenticated Web control to list eligible applied syncs, choose one, preview its exact paths, confirm, and restore through the shared service.
- A focused fixture creates a rollback record, confirms exact-plan restoration of newly created app/menu files, and verifies the final rolled_back status.

## Verification

- python3 -m py_compile lib/*.py: passed.
- bash -n lib/management.sh: passed.
- git diff --check: passed.
- Focused shortcut tests: 19 passed.
- Shared management/auth/session/Web transport/catalog tests: 90 passed, 1 skipped.
- Web UI and transport-focused tests after adding rollback controls: 24 passed, 1 skipped.
- Before Web rollback controls, bash scripts/repo_test.sh passed 860 tests with 1 skipped in 126.121 seconds. After adding the Web controls and catalog exposure, the full suite passed 861 tests with 1 skipped in 124.769 seconds. The runner printed its existing GUI-monitor diagnostic JSON after completion and exited successfully.
- Web/control checker and management catalog/transport focused tests: 32 passed, 1 skipped. The subsequent visible Firefox run passed its catalog, layout, shortcut-control, recovery-control, and terminal-renderer checks.
- No PRoot login, shortcut sync apply, GTK/Web GUI action, service restart, or active desktop restart was performed.

## Limits and next work

The exact installed CLI rollback list was read-only smoke-checked and returned an empty list. Web rollback controls passed visible Firefox 153.5.0 review on Native X11 :1 with the disposable ternuxx-replay-p4 alias; action controls were in-view at 742×881. See [visual report](web-shortcut-rollback-visual/report.json) and [screenshot](web-shortcut-rollback-visual/web-proot-shortcut-rollback-control.png). The checker reports browser_guest_login_performed=true and guest_profile_injection_possible=true; it used an isolated browser profile and did not start a managed terminal session. The protected default Debian guest was not selected. GTK/TUI actions remain open. Cross-process synchronization currently covers bulk sync/rollback paths only, not individual add/remove operations. Safe VirGL cleanup, broken-rootfs and cold-boot qualification, installed/source/runtime reconciliation, and full audit remain open.
