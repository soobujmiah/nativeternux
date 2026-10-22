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
- A focused fixture creates a rollback record, confirms exact-plan restoration of newly created app/menu files, and verifies the final rolled_back status.

## Verification

- python3 -m py_compile lib/*.py: passed.
- bash -n lib/management.sh: passed.
- git diff --check: passed.
- Focused shortcut tests: 19 passed.
- Shared management/auth/session/Web transport/catalog tests: 90 passed, 1 skipped.
- Full bash scripts/repo_test.sh: 860 tests passed, 1 skipped in 126.121 seconds. The runner printed its existing GUI-monitor diagnostic JSON after completion and exited successfully.
- No PRoot login, shortcut sync apply, GTK/Web GUI action, service restart, or active desktop restart was performed.

## Limits and next work

This is a source change in the live Native checkout; the exact installed CLI rollback flow still needs a read-only smoke check. The new service operations are authorized/classified for authenticated adapters, but Web controls and GTK/TUI actions are not implemented or verified. Cross-process synchronization currently covers bulk sync/rollback paths only, not individual add/remove operations. Safe VirGL cleanup, broken-rootfs and cold-boot qualification, installed/source/runtime reconciliation, and full audit remain open.
