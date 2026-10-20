Phase: `P3`

# Native timezone foundation — 2026-10-19

## Scope and baseline

Implemented a read-only Android timezone-database adapter, private persistent timezone preference, shared management operations, and CLI commands. Work ran in Native Termux via the owner-started SSH 8022 development channel, repository `$HOME/ternuxx`, branch `main`, HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`. The pre-existing worktree had 144 status entries before this increment and was preserved. Three timezone source/schema/test files were added. No commit was created.

Initial live state matched the previous handoff: Debian PRoot is installed at `$PREFIX/var/lib/proot-distro/containers/debian/rootfs`; PID 12830 is an active Debian login whose Ternuxx ownership is unverified; native GUI display :1 is reported running. None was entered, stopped, restarted, or changed.

## Implementation

- `lib/timezone_support.py` reads standard TZif data via `zoneinfo` or Android packed tzdata via a bounded parser. It rejects symlink/non-regular database files, insecure writable modes, bad indexes, invalid zone names and unsupported preferences. It reads at most 8 MiB and makes no network calls.
- The observed Android database is `/system/usr/share/zoneinfo/tzdata`, version `2025a`. This supplies actual IANA entries; no package was installed.
- A new installation defaults to `Asia/Dhaka`. An explicit `TERNUXX_INSTALL_TIMEZONE` may supply an installation preference; a persisted user selection takes precedence. Optional IP suggestion is not implemented.
- `tx mng timezone status|list|set IANA_NAME` uses the shared typed management service. Preferences persist as private schema-v1 `$TERNUXX_STATE_DIR/timezone.json`; writes are locked, fsynced and atomic. Invalid names and unsafe prior state fail closed.
- Cron-expression and daily definitions created through the CLI inherit the configured timezone when `--timezone` is omitted. An explicit schedule timezone is preserved; interval and one-time schedules remain instant-based.
- API scopes are exact: reads require `diagnostics.read`; `timezone.set` requires `timezone.manage`. Web does not receive this scope and its mutation transport remains disabled. TUI and GTK have no timezone configuration form.
- Catalog capability is present; no scheduler, execution engine, durable execution history, trigger delivery, or watchdog was added in this increment.

## Native observations

- `./tx mng timezone status` and installed `tx mng timezone status`: exit 0. Both reported default `Asia/Dhaka`, available=true, provider `android-packed-tzdata`, database version `2025a`, UTC offset `+0600`. No preference was written to the owner's live state.
- `./tx mng timezone list`: exit 0; 596 zone names returned and `Asia/Dhaka` was present.
- Live conversion: `2026-10-19T16:00:00Z` → `2026-10-19T22:00:00+06:00` for Asia/Dhaka.
- Live Cron preview at a fixed clock returned 23:00 Asia/Dhaka as `17:00Z` on consecutive days.
- DST preview through the live Android database: New York's nonexistent 2026-03-08 02:30 was skipped; repeated 2026-11-01 01:30 selected the first occurrence (05:30Z), then the next day's 01:30.
- `timezone.set UTC` was tested using a temporary state directory. It returned exit 0 and created mode-0600 preference and lock files; the temporary directory was removed. The real preference was unchanged.
- Invalid `NotA/RealZone` set attempt against temporary state returned exit 1 with `timezone_configuration_error`; no state file was written.
- Source `./tx` and installed `tx` returned equivalent status. Installed shim identity remained SHA-256 `a8735006203922cb7d7ab885e7fa1b85ca8608282de79d427d12a21a2511c401`, matching `scripts/tx-installed`.

## Verification

- Focused Cron/timezone: `python -m unittest tests.test_timezone_support tests.test_cron_registry -q` — 26 tests passed in 0.241 s, exit 0.
- Shared management/API/security + Cron/timezone: `python -m unittest tests.test_management_service tests.test_management_catalog tests.test_management_authorization tests.test_management_sessions tests.test_management_http_adapter tests.test_management_http_runtime tests.test_cron_registry tests.test_timezone_support -v` — 94 tests passed in 1.109 s, exit 0 (this shared cross-layer run preceded a catalog dependency-field cleanup; the post-cleanup focused catalog/Cron/timezone run passed 31/31 in 0.220 s, and the timezone-only rerun passed 11/11 in 0.171 s).
- Full Native Termux suite: `bash scripts/repo_test.sh` — 452 tests passed in 78.279 s, exit 0 (final run after the last source change).
- Python compilation, shell syntax, timezone JSON schema parse, and `git diff --check` — passed.
- Repository knowledge verification: `python3 -m tools.repo_knowledge verify` — 0 findings, exit 0.

## Not performed / remaining

No package installation, live timezone preference change, scheduler/job execution, boot/recovery delivery, PRoot login or lifecycle operation, GUI operation, reboot, SSH operation, Hermes task, Web/TUI/GTK mutation, or listener change occurred. The current installed runtime does not have a production scheduler or executor; these remain the next Cron gate. Boot/recovery delivery remains unqualified. Ternuxx-owned PRoot start/stop/recovery remains unimplemented; the active PID 12830 remains untouched. P3 stays in progress and P4 remains unqualified.

The default and CLI/API timezone preference are implemented. The installer does not yet show an interactive timezone selector; an explicit installation environment setting is supported. Dedicated Web, TUI and GTK timezone forms are not implemented. No current boot or scheduler behavior is inferred from this timezone work.


## Evidence

This is current P3 implementation and verification evidence. It records the commands, native observations, test results, and unresolved P3/P4 qualifications for the timezone foundation.
