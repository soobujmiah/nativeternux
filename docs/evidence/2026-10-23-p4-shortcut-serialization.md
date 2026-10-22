# P4 shortcut mutation serialization

Date: 2026-10-23
Runtime: Native Termux checkout through SSH 8022

Individual PRoot shortcut add/remove used to preview and mutate the launcher without acquiring the lock used by bulk sync and durable rollback. Concurrent client actions could therefore race while touching the same generated shortcut/menu state.

Confirmed individual add/remove now use the same private shortcut-sync/.lock inter-process lock as bulk sync and rollback. They recompute the exact preview after acquiring the lock and reject a stale plan before writing. If another serialized action already brought the selected shortcut to the requested state, the operation reports already_in_requested_state.

The shared management service passes its canonical Ternuxx state directory to the individual operation. No guest/rootfs action is involved.

## Verification

- Regression test holds the shared lock and proves confirmed individual add remains blocked until the lock is released; it then completes.
- Shortcut module tests: 21 passed.
- Focused shortcut and management service/API suite: 134 passed, 1 skipped.
- Full Native Termux suite: 869 passed, 1 skipped (126.703 seconds). The runner printed its existing post-suite GUI-monitor diagnostic after the successful test summary.
- git diff --check: passed.
