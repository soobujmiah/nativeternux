# P7 Native curated app lifecycle implementation — 2026-10-24

Phase: `P7`

Gate: PASS

## Acceptance criteria

- The exact three curated app IDs share typed list/preview/apply operations.
- CLI, TUI, authenticated Web, and GTK clients use the shared service and authorization; mutating actions require exact preview-bound confirmation.
- Package sources, index freshness, dependency closure, remove scope, plan expiry/replay, and drift fail closed.
- Full suite, document/link audit, and Native live read-only checks pass.

## Evidence

## Result

Implemented one typed Native Termux catalog for three stable app IDs: `process-monitor` (`htop`), `terminal-multiplexer` (`tmux`), and `directory-tree` (`tree`). `software.apps.list`, `software.app.preview`, and `software.app.apply` share one service and authorization contract across `tx app`, the TUI, authenticated Web client, and GTK Management Center. The catalog resource/domain now report these implemented operations as implemented.

Install/update previews require fresh signed Termux indexes, an exact configured official repository source, current candidate checks, and a full APT simulation with no removals or unreviewed package upgrades. The saved plan is private, expires after 15 minutes, and is single-use. Apply re-simulates the plan, compares its exact digest, pins resolved versions, and requires exact `INSTALL`, `UPDATE`, or `REMOVE` confirmation. Removal uses `--no-auto-remove` and refuses dependency drift. Requests cannot provide arbitrary package names or repository URLs. The Web route additionally requires the `software.manage` capability and mutation idempotency key. TUI prompts for the exact action word; CLI supports an interactive exact-word prompt or `--confirm`; GTK shows the exact plan before its explicit apply choice.

## Validation

- Full `env -u LD_LIBRARY_PATH bash scripts/repo_test.sh`: **706 tests passed** in 107.738 seconds.
- Curated lifecycle unit tests cover source allowlisting, stale indexes, dependency closure, simulation drift, no autoremove, private saved-plan state, expiry, one-shot apply, and status enumeration.
- Live read-only `tx app list` reported all three apps available from fresh configured indexes. Actual `tx app preview ... install` was run for all three using a temporary state directory. Results were `htop` 3.5.3 (1 new package), `tmux` 3.8 plus `utf8proc` 2.12.0 (2 new packages), and `tree` 2.3.2 (1 new package); each simulation reported zero removals and zero upgrades. Temporary plans were discarded. **No package was installed, upgraded, removed, or downloaded.**
- Native GTK C syntax check passed with `clang -fsyntax-only -Wall -Wextra` and Termux GTK4 compiler flags. Embedded Web JavaScript passed `node --check` with `LD_LIBRARY_PATH` unset. `bash -n` passed for the touched CLI scripts; Python compilation and `git diff --check` passed.
- The APT index and exact candidate versions are device-time snapshots and may change. Package apply behavior is tested with fixtures but deliberately not exercised on the live device; successful package execution and app workload behavior remain unqualified.

## Recovery and limitations

An expired or changed plan must be previewed again. If the process is interrupted after the record enters `applying`, inspect `dpkg`/APT state before creating a new plan. The curated catalog does not promise that package installation makes a desktop workload visible or accelerates graphics/audio. No app transaction was applied as part of this phase.
