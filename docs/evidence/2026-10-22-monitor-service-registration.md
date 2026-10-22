# GUI monitor service registration and replay — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Implementation

Implementation ran in the Native Termux checkout over SSH 8022. `tx gui monitor service status|preview-install|install --yes --plan-id PLAN_ID` provides Native-only fixed worker registration. The existing terminal broker API remains compatible. The installer accepts only the broker and GUI monitor IDs, validates executable ownership/mode and actual shell content, serializes registration, uses exclusive creation with execution disabled until the complete file is fsynced, and verifies running state and its published inode.

Rollback no longer treats equal bytes as proof of ownership. It refuses to signal/remove a competing definition. Failed stop retains its owned definition. The service run script prefers the canonical source checkout; installed fallback stays canonical. Disabled worker state is separately reported as running_idle and human-readable as “Ready; monitoring is off”. Catalog metadata asks for live installation status instead of asserting a permanently absent worker.

Human formatting also preserves exact paths/URLs, labels nonempty lists, and translates operation names. A live GTK bridge status exposed the original path punctuation corruption; a focused presentation regression now covers it.

## Failed observations and fixes

The pre-fix competing-publication regression failed because rollback removed the competing identical run file. Corrected tests also use real newlines, so invalid shell syntax is no longer hidden in a shebang comment.

Initial live registration reported failure before Runit discovered the new service directory. Stop could not be confirmed, so the definition was preserved; Runit subsequently started it. This was not counted as a successful installer return. Bounded discovery retry was added, then successfully exercised with a fresh, separate private Runit root. The existing live worker was not removed or reinstalled.

## Evidence

- Focused installer and policy tests verify competing-file preservation, lock serialization, stale plans, allowlisted service IDs, failed-stop retention, shell validation, symlink refusal and discovery retries.
- [Live deployment](2026-10-22-monitor-live-deployment.json) records installed/source identity, the worker's canonical module, running_idle, disabled focus/Activity/monitoring policy and live Linux GUI.
- [Fresh isolated replay](2026-10-22-monitor-service-replay.json) proves successful registration, idle default, two ticks exactly 30 seconds apart, unchanged workstation policy and confirmed private service exit/removal.
- The opt-in replay tool uses its own watcher, fixed service directory and private state. It never addresses existing Native services or a PRoot session.
- Final Native `bash scripts/repo_test.sh`: **715/715 passed in 107.040 seconds** after all source/presentation regressions.
- Focused installer 11/11, policy/catalog 14/14 and TUI/presentation 38/38 passed; CLI help contract and shell syntax passed.
- [Current Firefox result](2026-10-22-monitor-web-ui-check.json): exact 390/752/1440 CSS-pixel widths, no overflow, stable actions, response binding, hidden/authentication state and terminal dialog; recorded source hashes match current files. No managed guest was started.
- All 143 repository/new-tool Python files parsed; GTK source/bridge/binary/launcher/menu hashes match their existing installed identity. Live GTK bridge output shows the new idle label and preserves the exact log path.
- Deterministic repository verify reports 0 findings; strict README bridge and diff checks pass. Document inventory is current with 0 broken local links; read coverage is still incomplete.

## Remaining scope

Service registration controls in Web/TUI/GTK remain open; all four clients already share policy status/configuration. Android Activity/focus launch, later cold boot, every installed component, full guest reproducibility and all-document/P1–P3 requalification are not proven by this increment. The full [repository audit](../audit/REPOSITORY-AUDIT.md) remains active.

No workstation service, desktop or working Codex guest was stopped. The only exited service/watch process belonged to the private replay. Workstation monitoring policy remained off.
