# P3 - PRoot lifecycle manager increment - 2026-10-20

Phase: `P3`

## Repository and preservation

- Target: Native Termux $HOME/ternuxx. Branch main, HEAD 69e378eb33247678437bda4b2de9ab25f6bcb91d.
- Dirty status entries observed at this work session start: 169; final: 170. Existing changes were preserved. No reset, clean, stash, commit, push, package installation, or boot configuration change.
- The task's earlier report cited 166 status entries; current inspection found 169, treated as a historical difference rather than overwriting any state.
- PRoot implementation and tests were existing untracked worktree entries at this session start and were extended in place. Relevant touched files: lib/proot_sessions.py, lib/management_service.py, lib/management.sh, lib/management_authorization.py, lib/management_sessions.py, lib/management_catalog.py, tests/test_proot_sessions.py, tests/test_management_service.py, tests/test_launch_commands.py, docs/architecture/PROOT-SESSIONS.md, docs/architecture/MANAGEMENT-API.md, docs/architecture/CAPABILITY-MATRIX.md, CURRENT_STATE.md, and generated docs/PHASE-STATUS.md.

## Implemented

- Added a fixed, validated profile inventory through the existing session manager and management service:
  - isolated-probe: bounded headless diagnostic process; no display or host-home binding.
  - debian-interactive: foreground Debian login for guest user sbj using the same Debian/shared-tmp selection as the db alias; requires a TTY, starts no GUI or services.
- Added preview-first CLI profile start and exact-session stop, requiring a fresh plan and explicit confirmation for mutations.
- Added read-only recovery inspection at tx mng proot recover SESSION_ID. It never adopts, rewrites, removes, or signals a record.
- Session registry schema v2 preserves v1 reads, private atomic storage, and process/rootfs/launcher identity evidence. The per-session marker is carried into guest argv because the launcher does not preserve the host marker environment.
- Failed ownership verification leaves a record unverified and fail-closed. Stop sends SIGTERM only to the exact verified Ternuxx session group, waits boundedly, and never force-signals.
- Web, TUI, and GTK remain read-only for this PRoot lifecycle; the Web runtime does not receive proot.session.manage. CLI and shared typed API expose the supported start/stop flow. No shell string is accepted.

## Runtime evidence

- Current read-only profile inventory found proot-distro at /data/data/com.termux/files/usr/bin/proot-distro, Debian rootfs at /data/data/com.termux/files/usr/var/lib/proot-distro/containers/debian/rootfs, rootfs device/inode 65086:3240111, and both fixed profiles available.
- A harmless disposable PRoot headless session completed start, show, stop-preview, confirmed stop and final stopped verification using an isolated temporary registry. A second disposable probe in the default Ternuxx registry was also stopped after exact identity checks. These were real PRoot processes, not fixture-only tests; no Debian package/rootfs contents were changed.
- An early probe did not expose its expected marker. Stop was refused; the process was allowed to expire naturally. Its default-registry record remains unverified. Recovery inspection reported process identity mismatch/absent, signal_allowed=false and action=retain_record_no_signal. The record was not deleted or repaired.
- The interactive profile was inventoried and previewed. A non-TTY attempt was rejected before session creation. No live interactive shell was opened.
- These observations prove a bounded disposable session lifecycle only. They do not qualify detached workstation supervision, normal interactive operation, process-tree recovery, GUI/X11/application windows, service management, or boot-time PRoot.

## Cron and Termux:Boot compatibility

- Read-only tx mng cron status: scheduler stopped, process not running, no jobs/executions.
- Read-only tx mng boot cron status: com.termux.boot confirmed installed/enabled; 20-ternuxx-cron is not configured; scheduler stopped; actual device-boot delivery not yet verified.
- The Termux:Boot script and existing boot files were not changed. No production scheduler/job was started and no reboot occurred.

## Evidence

### Verification

- python3 -m unittest tests.test_proot_sessions tests.test_management_service tests.test_management_sessions tests.test_management_authorization tests.test_launch_commands tests.test_termux_boot_cron -q: 71 passed, 3.641s, exit 0.
- python3 -m unittest tests.test_cron_daemon tests.test_cron_scheduler tests.test_cron_execution tests.test_termux_boot_cron -q: 29 passed, 6.191s, exit 0.
- bash scripts/repo_test.sh: 493 passed, 90.044s, exit 0.
- python3 -m compileall -q lib tests: exit 0.
- bash -n lib/management.sh: exit 0.
- python3 -m json.tool schemas/proot-session-registry.schema.json: exit 0.
- git diff --check: exit 0.
- python3 -m tools.repo_knowledge verify: 0 findings.
- Current API allowlist count: 77 operations.

## Protected state and qualification

No protected existing PRoot session, legacy db/tx db/x.sh/xgo/killx workflow, Debian rootfs contents, floating X11 GUI, SSH service, Hermes task/configuration, production Cron, Termux:Boot file, or unknown listener was changed or stopped. Only the disposable PRoot test sessions created for this work were stopped. A current PID-level comparison with the historical development PID was not used to infer ownership.

P3 remains in progress. P4/general workstation and GUI lifecycle remains unqualified. The next bounded phase is to validate the foreground interactive profile in an owner-controlled terminal and then design a distinct supervised workstation profile only after reliable attach/recovery ownership can be demonstrated. Do not redirect legacy aliases or add GUI/boot startup as part of that phase without separate validation.
