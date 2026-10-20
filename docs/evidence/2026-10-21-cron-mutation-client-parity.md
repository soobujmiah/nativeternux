# Cron mutation parity across management clients — 2026-10-21

Phase: `P3` — remains in progress.

## Change

Added one shared Cron job mutation contract:

- `cron.jobs.mutation.preview` stores a private plan and shows its before/after state without changing the job registry.
- `cron.jobs.mutation.apply` requires the exact plan ID and explicit confirmation. Plans expire after 15 minutes and fail if the registry changed after preview.
- The plan store is private (`0600`), bounded, and protected by the Cron registry lock. Existing direct service CRUD operation IDs are no longer exposed.
- Authorization maps both operations to `cron.manage`. The Web session requests that scope and applies CSRF plus durable idempotency to preview/apply requests.

CLI, TUI, Web, and GTK all call these shared operations. Each client has a guided create/update/remove flow. CLI, TUI, and Web also expose enabled-state changes; GTK currently supports create, rename, and remove. No client implements arbitrary shell actions or bypasses the registered Cron action list.

The installed GTK management-center binary was rebuilt from repository source with `scripts/install-management-center.sh`. Its self-check reported GTK 4.24.1, its version reported Ternuxx Management Center 0.1, and the installed C/bridge source hashes match the checkout. Before replacement, the previous binary, launcher, and identity were verified against their identity record and saved under the private Native Termux rollback directory:

`$HOME/.local/share/ternuxx/rollback/management-center/2026-10-21`

## Verification

- Focused Cron, timezone, TUI, Web-runtime, and GTK-bridge tests: **88/88 passed**.
- Full Native Termux repository suite: **627/627 passed in 134.775 seconds** via `bash scripts/repo_test.sh`.
- GTK4 C source: `clang -fsyntax-only -Wall -Wextra apps/management-center/management-center.c $(pkg-config --cflags gtk4)` passed.
- `git diff --check` passed.
- Repository knowledge verification: **0 findings** (rerun after docs update below).

No live Cron job was created, changed, or removed. The scheduler was not started, stopped, or restarted. The Native XFCE `:1` session and Debian PRoot were not restarted or modified. The GTK application window was not opened or visually re-tested in this iteration; the installed artifact was checked without restarting the running desktop or application.

## Remaining P3 work

The installed Termux:Boot helper reconciliation was completed in the later same-day P3 continuation; see [boot-helper reconciliation evidence](2026-10-21-boot-helper-reconciliation.md). Remaining P3 recovery/concurrency gates and actual cold-boot delivery are still unqualified. No reboot or session closure was performed.

## Evidence

This is incremental P3 evidence, not a phase-completion claim. Source, tests, deployment identity, and remaining gates are recorded above.
