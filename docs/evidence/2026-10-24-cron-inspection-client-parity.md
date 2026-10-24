# Cron inspection client parity — 2026-10-24

## Change

The shared management service already exposed `cron.jobs.show`, `cron.jobs.next_runs`, and `cron.executions.show`, but the guided TUI, Web, and GTK clients did not provide entry points for those reads. Added selection-based detail and next-run actions in TUI/Web, and typed ID-based inspection controls in GTK. All routes dispatch only to the existing shared service operations; GTK's bridge accepts a narrow action and validated identifier rather than arbitrary operation names or paths.

## Verification

- Focused client/bridge/API contracts: **103 tests passed**.
- Full `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh`: **727 tests passed** in 93.501 seconds.
- GTK4 `clang -fsyntax-only -Wall -Wextra` passed.
- `git diff --check`, document inventory/link check, and `python3 -m tools.repo_knowledge verify` passed; inventory reported 0 broken links and current path/hash coverage.
- Live Native read-only `tx mng cron status` reported scheduler stopped, no jobs, and no unresolved executions. `tx mng cron jobs list` returned an empty registry. No live job-detail or execution-detail request could be demonstrated because the registry has no records; behavior is covered by fixture tests.
- No scheduler, job definition, service, desktop, or Termux lifecycle state was changed.

## Remaining limits

This closes only Cron read-detail access. Cron validation forms, scheduler boot/recovery delivery, cancellation/retry, broader client action parity, accessible/visual acceptance, and clean-device qualification remain open. It does not change the release blockers recorded in `CURRENT_STATE.md`.
