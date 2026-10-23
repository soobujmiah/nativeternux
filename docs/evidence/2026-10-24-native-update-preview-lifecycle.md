# Native core package update preview lifecycle

Phase: `P4`

Date: 2026-10-24

## Change

Added an explicit Native core update preview path:

```sh
tx install update preview
tx install update apply PLAN_ID
```

The concise install forms are `tx install preview` and `tx install apply PLAN_ID`. Existing flag forms remain supported. Update planning selects installed Ternuxx core packages with a newer candidate from the expected official Termux repository, pins each direct candidate, simulates the complete dependency closure, and binds the saved preview ID to the operation kind and exact APT result. Apply rebuilds the plan and refuses stale IDs, removals, non-official package sources, missing requested upgrades, or detected downgrades. No package indexes or installed packages were changed during this work.

## Evidence

- Native focused package-plan tests: 15 passed.
- Native full source suite: 899 tests passed, 1 skipped (Python 3.14.6; `scripts/repo_test.sh`, final run).
- `bash -n lib/phases.sh`, `git diff --check`, and `tx help install` completed successfully.
- Search of the canonical Native checkout found no prohibited GitHub Termux:X11 repository URL.

## Remaining boundary

This implements a preview-bound updater for the fixed Native core package set. It does not add durable package artifact retention, immutable repository snapshots, a permanent cross-date version lock, optional Native workload selection, or package lifecycle parity in Web, GTK, TUI, and VTE clients. Termux rolling repositories can stop serving prior versions; exact replay across dates therefore still requires an artifact mirror/snapshot strategy. No live update was applied.
