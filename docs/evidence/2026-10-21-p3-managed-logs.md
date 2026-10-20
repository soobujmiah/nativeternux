# P3 bounded Native management logs - 2026-10-21

## Implementation

Added typed read-only operations `management.logs.list` and `management.logs.read` to the shared management service. The source allowlist contains only the Ternuxx Cron scheduler log and the secret-free management API audit trail. Callers cannot pass filesystem paths.

Reads require a private Ternuxx state tree and same-user regular files with mode 0600; source directories must be same-user private directories with mode 0700. Symlinks, unknown IDs, changed identities, and invalid limits fail closed. Reads are limited to the last 256 KiB and at most 300 lines; ANSI/control characters are removed and long lines are capped. Audit output reconstructs a safe field set and omits request/session identifiers.

The CLI exposes `tx mng logs list` and `tx mng logs read SOURCE_ID`. TUI, Web, and GTK call the same typed operations. Web has an on-demand source picker and bounded viewer. GTK has source-specific actions; TUI prompts for an available source. No Android-global or arbitrary application logs are exposed.

## Native evidence

Read-only live Native Termux calls through `tx mng logs list` found both allowlisted sources. Reading the management audit returned operation, capability, event, time, status, and duration fields; session references and request IDs were absent. The Cron scheduler log was present but empty. No log file was created or changed by the read.

The installed GTK Management Center was updated atomically by `scripts/install-management-center.sh`. Binary SHA-256: `2393e252165ecdd2a53c2b3b69f9b1e58e8949896b90bd2d33324f27ae45020f`. The existing Native :1 desktop and Termux session were not restarted. GTK source was compiled, but the new log actions were not visually exercised; Web browser rendering and TUI keyboard interaction also remain unverified on-device.

## Verification

- Management/log-reader/TUI/Web/GTK bridge focused tests: **114 passed** before the dedicated log-reader fixtures were added.
- New log-reader fixtures: **4 passed**.
- Full Native Termux repository suite: **650 passed** in 103.766 seconds.
- GTK C syntax compile, Python compilation, shell syntax, and `git diff --check`: passed.
- Live `tx mng logs list` and `tx mng logs read` returned bounded results.
- No service, scheduler, desktop, SSH, PRoot session, or Android setting was changed.

P3 remains active. The operation is source-integrated across all four clients, while visual acceptance is still required. Cold-boot delivery remains unverified and must be qualified in its separate device-boot window.
