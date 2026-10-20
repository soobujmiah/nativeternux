# Cron history across management clients — 2026-10-20

Phase: `P3` (incremental; phase remains in progress)

## Change

Added a bounded, read-only recent execution-history action for the existing Cron
registry resource in TUI, Web, and Native GTK. Each client requests at most 20
records through the existing `cron.executions.list` operation with
`diagnostics.read`. No scheduler was started and no job definition or execution
was changed. TUI supports both `H` and the guided `a` action; Web and GTK show a
resource-specific history button. GTK delegates through its typed local bridge.

Updated the capability matrix to reflect the new client coverage and continued
limitations. These clients still do not mutate Cron jobs or control the
scheduler.

## Verification and live installation

On Native Termux through the existing SSH 8022 session:

- `bash scripts/repo_test.sh` — 583/583 passed.
- Focused TUI suite — 19/19 passed.
- GTK bridge and HTTP runtime suites — 25/25 passed.
- GTK4 C syntax check with `clang -O2 -Wall -Wextra -fsyntax-only ...` — passed.
- `git diff --check` — passed.
- `python3 -m tools.repo_knowledge verify` — 0 findings.
- `./tx mng center install` — passed; installed GTK artifact SHA-256:
  `800197c008297db104f3a8ca64be16cf49c2d4a77ac973819f1f99d536243f2b`.

The active GUI session was not restarted, so its running GTK process does not
load the new binary until the owner next launches the management center. No
visual interaction was performed. The current Codex, SSH 8022, and native
workstation sessions were left running.

## Remaining client gaps

The operation-by-operation list in [the capability matrix](../architecture/CAPABILITY-MATRIX.md)
remains authoritative. TUI/Web/GTK still lack Cron mutation and timezone
configuration; GTK lacks PRoot app/session actions; browser rendering and GTK
visual usability still need owner-operated review. This change does not complete
P3 or claim full client parity.
