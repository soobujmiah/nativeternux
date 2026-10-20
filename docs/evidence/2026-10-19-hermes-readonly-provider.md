# 2026-10-19 — Native Hermes read-only provider slice

Phase: `P3`

## Evidence

### Baseline

- Native runtime: Termux Android/aarch64; repository `$HOME/ternuxx`, branch `main`, starting HEAD `69e378e`.
- The incoming dirty worktree had 134 status entries. No pre-existing changes were reset, cleaned, or reverted. At final review it had 139 entries, five more than baseline: the adapter, two focused test files, architecture documentation, and dated evidence. Existing dirty files remained dirty.
- Hermes executables resolve under `$PREFIX`: `hermes` and `hermes-agent`. The installed package is `hermes-agent`; reported version is `v0.22.0+canary.20261014T070054Z (2026.9.24)`. `$HOME/.hermes` mode is 0700 and `$HOME/.hermes/config.yaml` mode is 0600. Configuration values and history were not read into this report.
- The installed Hermes CLI documents `cron status` and `cron list`. On this device, read-only `hermes cron status` reported no scheduler serving profile `default`; read-only `hermes cron list` reported no scheduled jobs. `$HOME/.hermes/cron` contained zero regular files at the bounded depth checked. These are observations at the test time, not a promise about future state.

### Implemented

- Added `lib/hermes_adapter.py` and the shared API operation `agent.hermes.status`, scoped to `diagnostics.read` and classified read-only.
- The adapter checks the exact Native Termux executable path, uses an argument vector and minimal environment, applies 5-second version and 8-second status timeouts, parses only known status markers, discards raw output, and maps unexpected output/timeouts to `unknown`.
- Added optional Hermes resource metadata to catalog v2. It explicitly reports independent Hermes ownership, disconnected mode, and task/scheduler mutations as planned/unsupported.
- Added `tx management hermes status`; the installed `$PREFIX/bin/tx` shim still matches `scripts/tx-installed` by SHA-256 and dispatches into this repository checkout.
- No Hermes task content, execution records, configuration values, or history were exposed. No task ran; no scheduler, gateway, boot profile, or Hermes configuration was changed.

### Tests and commands

- Focused adapter: `python3 -m unittest discover -s tests -p "test_hermes_adapter.py" -v` — 5/5 passed.
- Focused provider/API: `python3 -m unittest discover -s tests -p "test_hermes*.py" -v` — 9/9 passed.
- Authorization: `python3 -m unittest discover -s tests -p "test_management_authorization.py" -v` — 5/5 passed.
- Catalog: `python3 -m unittest discover -s tests -p "test_management_catalog.py" -v` — 5/5 passed.
- Full Native Termux suite: `bash scripts/repo_test.sh` — 423/423 passed in 109.763 seconds, exit 0.
- `bash -n lib/management.sh lib/help.sh`, Python compilation of the adapter/service/policy/catalog/session modules and new tests, HTML parser check, `python3 -m tools.repo_knowledge verify` (0 findings), and `git diff --check` passed.
- Live read-only command: `$PREFIX/bin/tx management hermes status` — exit 0; response reported provider available, exact Hermes version, profile `default`, scheduler `not_running`, health `not_ready`, task operations unsupported. Live catalog filtering returned the same resource and `diagnostics.read` scope.

### Source/install identity

- `$PREFIX/bin/tx` and `scripts/tx-installed`: SHA-256 `a8735006203922cb7d7ab885e7fa1b85ca8608282de79d427d12a21a2511c401` (match).
- Installed Hermes executable `$PREFIX/lib/hermes-agent/bin/hermes`: SHA-256 `d77067ba2593a4d91f01d29c5de561af49bc1521c5eca9522d140522b36b6765`.
- Runtime import resolved `hermes_adapter` to `$HOME/ternuxx/lib/hermes_adapter.py`; no separate installation or service deployment was required.

### Not implemented / limitations

- Ternuxx Cron is still not implemented: no job registry, cron-expression parser, interval/daily/one-time scheduler, execution ledger, retry/timeout engine, cancellation, boot semantics, missed-run policy, or independent watchdog was added.
- Hermes task listing, validation, preview, execution, cancellation, logs/history, configuration management, and schedule bridge remain unsupported. Scheduler state remains Hermes-owned and independent.
- No UI action flow was added for Hermes task operations. The shared catalog advertises only status inspection; the CLI is the live entrypoint for this increment.
- Independent Ternuxx PRoot lifecycle remains blocked pending verified rootfs relationship/ownership, shared-resource and concurrency evidence. Existing `:0` record was not changed.
- No PRoot application, GTK window, browser, clipboard, GUI, SSH, audio, Termux:Boot, or reboot qualification was performed in this increment.

### Safety and rollback

The change adds a read-only provider probe and metadata only. Rollback, if required, is limited to reverting the exact Hermes adapter/API/catalog/test/doc additions through a reviewed change; do not use broad checkout/reset commands because this worktree contains unrelated owner changes. Ports 8022, 8023 and 8765 and existing services/rootfs were not managed by this operation.
