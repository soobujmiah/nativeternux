# Canonical management namespace and Cron foundation — 2026-10-19

Phase: `P3`

## Evidence

### Verified baseline

- Implementation ran in Native Termux at `$HOME/ternuxx` through the existing manually managed development connection on SSH port 8022. Native `$HOME` was `/data/data/com.termux/files/home`; `$PREFIX` was `/data/data/com.termux/files/usr`; Termux version was `0.119.0-beta.3`.
- Branch remained `main`, HEAD remained `69e378eb33247678437bda4b2de9ab25f6bcb91d`. The worktree was already dirty (143 status entries before this increment); no changes were reset, cleaned, or committed.
- Installed `$PREFIX/bin/tx` and repository `scripts/tx-installed` SHA-256 both equal `a8735006203922cb7d7ab885e7fa1b85ca8608282de79d427d12a21a2511c401`.
- Read-only PRoot status and `proot-distro ps` found installed Debian and one active `debian` login session, PID 12830, parent PID 11238. Process ownership/session role was not attributed. The session was preserved. The rootfs path `$PREFIX/var/lib/proot-distro/containers/debian/rootfs` exists as owner `u0_a490`, mode `0755`. `~/db/droot` and `~/ternuxx/db/droot` are absent; `db` is an existing shell alias to `proot-distro login debian --shared-tmp --user sbj`, `xgo` aliases `~/x.sh`, and `killx` is a non-terminating advisory alias. `proot-distro info debian` is unsupported by the installed proot-distro command. No guest was entered or stopped.

### Implemented

- `tx mng` is now the canonical public management namespace. `tx management` remains a warning-emitting deprecated compatibility alias; unrelated top-level commands remain available. Added `tx mng proot status` as an explicit read-only shared-service route; the existing `tx proot` commands remain intact.
- Added the version-1 persistent Cron Job Registry in `lib/cron_registry.py`, schema `schemas/cron-job-v1.schema.json`, and shared typed API operations for status, list, show, validate, next-run preview, create, update and remove. Storage uses private modes, atomic replacement and serialized mutations. Corrupt, unsafe, unsupported or locked stores fail closed. Fixture tests use temporary state.
- Supported schedule categories are numeric five-field cron, anchor-based interval, calendar daily/specific, and one-time. Timeouts, bounded retries, missed-run, concurrency and output policies are validated. Preview does not execute a job.
- `run_after_device_boot` and `run_after_scheduler_recovery` persist as separate booleans. A pure policy planner tests event identity, duplicate suppression, device-boot precedence for same-boot events, disabled-job exclusion, and one-time completion exclusion. Event claims are not persisted and no trigger invokes work.
- CLI job definitions default disabled. Read operations require `diagnostics.read`; mutations require `cron.manage`. Web bootstrap deliberately does not grant `cron.manage`. TUI, Web and GTK expose only registry status/list reads at present. Job execution, production scheduling, execution history, Android boot delivery, recovery delivery and watchdog are unavailable, not simulated.
- GTK source and bridge were installed through `./tx mng center install` after their source hashes differed from the installed identity. Installed client `--self-check` passed (GTK 4.24.1). New installed identity records current C and bridge hashes and installed binary SHA-256 `ec5ac46112719e0746ee0970f328b5614978f34ab0c69001fb85fac026c94478`; launcher SHA-256 is `e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd`. No GTK window was opened.
- Current PRoot docs now permit reuse of the existing rootfs, while limiting lifecycle authority to a uniquely identified Ternuxx-started instance. The active Debian session remains unowned/unverified from Ternuxx's perspective; start/stop/recovery were not implemented or invoked.

### Actual Native Termux read-only checks

- `./tx mng cron status` — exit 0; `registry_schema_version=1`, `job_count=0`, `scheduler=not_installed`, `process=not_running`, execution unsupported, boot delivery not qualified, recovery delivery not installed.
- `./tx mng cron jobs list` — exit 0; empty persisted registry.
- `./tx mng cron jobs validate --job-name "Safe preview" --job-action diagnostics.doctor --schedule-type cron --cron-expression "*/15 * * * *" --timezone UTC` — exit 0; typed preview validated with enabled false. No job was created or executed.
- `./tx mng proot status` — exit 0, read-only; Debian installed, one host PRoot process candidate, ownership unverified, `guest_entered=false`.
- The `proot-distro list` read-only command reported installed `debian`; `proot-distro ps` reported the existing login session. No PRoot operation was issued.
- No Hermes command/configuration/job was re-run or changed. Historical read-only provider evidence remains the source for prior Hermes inspection; the adapter boundary remains status-only.

### Tests and static checks

- Focused: `python3 -m unittest discover -s tests -p test_cron_registry.py -v` — 15/15 passed after final code edits.
- Focused: `python3 -m unittest discover -s tests -p test_launch_commands.py -v` — 9/9 passed after final code edits.
- Complete Native Termux suite: `bash scripts/repo_test.sh` — 441/441 passed in 94.684 seconds; command exit 0.
- Python compilation for Cron, management service/policy/catalog/sessions, TUI and desktop bridge — exit 0.
- `bash -n` for `bin/tx`, `lib/management.sh`, and the GTK installer — exit 0.
- `python3 -m json.tool schemas/cron-job-v1.schema.json` — exit 0; HTML parser accepted `lib/management_web_ui.html` — exit 0.
- `python3 -m tools.repo_knowledge verify` — 0 findings.
- `git diff --check` — passed, exit 0. Final repository knowledge verification reported 0 findings; final branch/HEAD were unchanged and the worktree had 144 status entries (one more than the initial snapshot).

## Acceptance criteria

This increment establishes canonical `mng`, a persistent validated job-definition store, deterministic schedule previews and independently stored boot/recovery policy fields. It does not qualify a production scheduler, job execution, Android boot/recovery trigger delivery, UI mutation parity, or an independent live PRoot lifecycle. P3 remains in progress; P4 remains unqualified. No reboot, production job, SSH/GUI/audio lifecycle operation, Hermes task, PRoot launch/stop, or Activity/focus monitoring action was performed.
