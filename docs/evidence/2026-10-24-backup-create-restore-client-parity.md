# Native backup creation and restore client parity — 2026-10-24

## Change

Added preview-confirmed configuration backup creation and boot-profile restore apply to the TUI, Web, and GTK management clients. Each client obtains a read-only preview, displays its exact plan, requires an explicit confirmation, and submits that same plan ID to the shared management service. Web sessions now request the existing `state.backup` and `state.restore` capabilities; mutating calls retain CSRF and idempotency protections. The GTK desktop bridge accepts only fixed typed actions, constrained backup names/IDs, and 64-character plan IDs. The GTK confirmation defaults to Cancel. Restore apply continues to create its rollback snapshot through the service.

No live backup or restore was executed during implementation.

## Verification

- Focused client suite: 122 tests and 84 subtests passed.
- Full `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh`: **735 tests passed** in 92.804 seconds. `python3 -m tools.repo_knowledge verify`, document inventory/link checks, and `git diff --check` passed with 0 findings.
- GTK4 C syntax check: `clang -fsyntax-only -Wall -Wextra` passed.
- Runtime backup inventory and recovery state were not mutated.

## Remaining limits

Rollback apply, operation resolution, continuity checkpoint preparation/verification, and broader recovery action parity remain CLI-only. No restore was applied and no reboot was requested. The existing public release gates remain open.
