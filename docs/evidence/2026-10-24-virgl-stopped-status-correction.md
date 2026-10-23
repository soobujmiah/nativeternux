# VirGL stopped-state status correction — 2026-10-24

## Finding

Read-only Native Termux checks showed `tx virgl status --display :1 --json` reporting `state=stale` and `identity=recorded-process-absent`, while the exact socket file and server process were both absent. `tx virgl stop --display :1` separately reported no active record and made no change. The status path did not account for an owner record whose lifecycle status was already `stopped`.

## Change

`virgl_lifecycle.status()` now reports `stopped` for a stopped owner record when no matching process or socket exists. A contradictory matching live process or a replacement socket reports `unsafe`; a remaining socket matching the recorded inode remains `stale`. Repeated stop now reports the recorded Ternuxx owner and `stopped` instead of `unknown`/`unchanged`. Existing active-client visibility and stop refusal logic is unchanged.

## Verification

- Focused source fixtures: `python3 -m unittest discover -s tests -p test_virgl_lifecycle.py -v` — 11 passed in 15.162 seconds (run from the PRoot Debian development workspace against the Native checkout source).
- Native Termux full source suite: `bash scripts/repo_test.sh` through SSH 8022 — 896 tests passed, 1 skipped, 140.777 seconds, exit status 0.
- The full suite printed one GUI-monitor negative-path JSON message requiring Native Termux; unittest completed successfully.
- Live before/after through the Native `tx` shim: status changed from `stale` to `stopped` with `recorded-stopped-no-process-or-socket`; repeated `tx virgl stop` now returns the same Ternuxx-owned stopped state without signaling a process. Read-only `ps` found no VirGL server, and the exact socket path was absent. No live VirGL process, socket, desktop, or PRoot guest was changed.
- The replacement-socket regression verifies that an unrecorded replacement socket is reported `unsafe`, is not removed, and is not treated as stopped.

## Remaining limits

This fixes stopped-state reporting only. If a VirGL server is active and client visibility is unknown, stopping remains refused. Visible rendering, nested guest acceleration, and audio remain separate unverified P4 gates. Native package version locking, clean-device reproduction, and existing-guest migration/rollback also remain open.

## Evidence

Phase: `P4`

Current Native Termux status and bounded fixture/full-suite evidence.
