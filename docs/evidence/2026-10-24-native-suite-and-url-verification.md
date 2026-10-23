# Native suite and prohibited-link verification — 2026-10-24

## Revision and target

- Canonical Native Termux checkout: `$HOME/ternuxx`
- Branch and revision: `main`, `79023615bbff7b4e9bf90f34b28bc146f3679e9f`
- Execution path: authenticated development SSH on port 8022; runtime identified as Android Termux (`$PREFIX=/data/data/com.termux/files/usr`).
- Worktree was clean before recording this evidence.

## Checks

- Command: `bash scripts/repo_test.sh`
- Result: **895 tests passed, 1 skipped**, 115.513 seconds, exit status 0.
- The suite emitted one JSON error line from a GUI-monitor command requiring Native Termux; the unittest runner still completed successfully. This is not physical GUI or PRoot integration evidence.
- Exact-string search for the prohibited Termux:X11 GitHub repository URL in tracked `HEAD` returned no matches. The removal is present in the current branch history (`ddad8ce`, “docs: remove prohibited external X11 project links”).

## Limits and next action

This run qualifies only the source test suite on this Native Termux runtime. It does not close P4 clean-device reproducibility, durable package locking, existing-guest migration/rollback, or visible GUI/accelerator acceptance. Keep P4 active and continue with the highest-priority unresolved acceptance gate in `docs/PHASE-STATUS.md`.

## Evidence

Phase: `P4`

Native Termux source-suite rerun and current-main prohibited-link check.
