# Native recovery resolution client parity — 2026-10-24

## Change

Added exact-preview-confirmed restore rollback apply and unresolved-operation reconciliation to TUI, Web, and GTK. Clients select operation records from current recovery status, review the shared service preview, and require an explicit `ROLLBACK` or `RESOLVE` confirmation before submitting the same plan ID. Operation resolution is limited to unresolved states in the TUI, Web flow, and shared service validation. Web uses `recovery.manage`, CSRF proof, and idempotency keys. The GTK bridge accepts only fixed operation names, 32-character operation IDs, and 64-character plan IDs; its confirmation defaults to Cancel.

No live journal resolution or rollback was applied.

## Verification

- Focused TUI/Web/GTK client suite: 126 tests and 102 subtests passed. Full `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh`: **738 tests passed** in 88.499 seconds. GTK4 `clang -fsyntax-only -Wall -Wextra` and Python byte-compilation checks passed.
- Live recovery inventory remains read-only; no service, desktop, or reboot action was run.

## Remaining limits

Continuity checkpoint preparation/verification and reboot-test preparation/verification remain CLI-only. A device reboot test, clean-device qualification, visual acceptance, and public release gates remain open.
