# Cron runtime and PRoot isolated probe evidence  2026-10-19

Phase: `P3`

## Evidence

## Repository and preservation

- Target: Native Termux checkout at $HOME/ternuxx.
- Branch and HEAD before/after: main / 69e378eb33247678437bda4b2de9ab25f6bcb91d.
- Initial worktree status entries for this increment: 156. They were preserved; no reset, clean, stash, checkout, commit, or push was used.
- Pre-existing local changes were already extensive. This increment changed only its implementation/test/documentation paths listed below. Final worktree status entries: 161; this includes the newly recorded evidence file.
- Source CLI: bin/tx SHA-256 b8eead51657f5758184493aa93db559f846cf92bc0b269728b6b4a9b37f2e562.
- Installed entrypoint: $PREFIX/bin/tx SHA-256 a8735006203922cb7d7ab885e7fa1b85ca8608282de79d427d12a21a2511c401. It is a thin shell wrapper that dispatches to $HOME/ternuxx/tx, which dispatches to bin/tx; the different hashes are expected. No installed artifact was overwritten or reinstalled.

## Cron runtime

Implemented:

- lib/cron_daemon.py adds an explicitly started native-Termux daemon, bounded polling, a detached process, and graceful SIGTERM shutdown. It is not registered with Termux:Boot and does not start from a status/UI query.
- lib/cron_scheduler.py reports process liveness, lease ownership, and recent dispatch health separately. The daemon holds the existing advisory lease and private PID/process-start/instance record. Polls validate the lease before dispatch.
- A due schedule is resolved using the existing registry/timezone engine and its stable event identity; an atomic claim is acquired before the existing typed action executor runs.
- tx mng cron start requires --yes because enabling polling can run already-enabled jobs. The poll interval is bounded to 160 seconds. tx mng cron stop requires --yes and verifies the recorded instance marker, command, PID start time, lease and instance before signalling. Shutdown is graceful; no force-kill path exists.
- cron.scheduler.start/stop use the shared management service and the narrow cron.scheduler.manage scope in authenticated transports. Current Web bootstrap does not grant this scope. Web, TUI and GTK remain read-only for scheduler lifecycle.

Isolated runtime proof:

- A temporary private registry received one enabled one-time job using the fixed harmless scheduler.self_test action, scheduled three seconds in the future.
- The daemon acquired its lease, polled, claimed the stable event once, ran the actual allowlisted subprocess path, and persisted one succeeded record with exit code 0.
- A subsequent poll did not create a duplicate ledger record.
- The daemon was stopped by verified identity. The temporary registry was removed by its temporary-directory context.
- This is isolated runtime evidence, not production job execution. The production registry remains empty and the daemon remains stopped.

Policy limits:

- The current poller dispatches only missed_run_policy=skip, max_attempts=1 and skip_overlap. Other retry, queue, cancellation and catch-up policies are rejected or unavailable.
- Device boot and scheduler-recovery delivery remain unqualified and separate. No boot integration was installed or enabled.
- Event claims prevent duplicate dispatch for the same stable event. A crash after an external side effect but before completion persistence remains uncertain; exactly-once external side effects are not claimed. Unresolved actions are not automatically replayed.
- No production job, scheduler service or boot trigger was run/enabled.

## PRoot lifecycle probe

- Read-only discovery confirmed proot-distro and Debian rootfs at $PREFIX/var/lib/proot-distro/containers/debian/rootfs. The active proot-distro inventory showed the existing Debian login PID 12830; it was not signalled or modified.
- proot-distro login --help showed --minimal is an isolated mode with only /dev, /proc and /sys mounted. The options --isolated and --minimal are mutually exclusive, so the implementation uses --minimal.
- lib/proot_sessions.py adds a private versioned registry, validated rootfs/launcher device+inode identity, stable Ternuxx session IDs, environment marker, PID/start-time and new session/process-group identity. Only fixed profile isolated-probe is executable in this increment; it runs /bin/sleep and is not a workstation or GUI session.
- A disposable probe was started against the discovered Debian rootfs in --minimal mode with temporary Ternuxx state. Session ID proot-1975bb6b986141a29ee2f3c967e5142d, PID/process-group 17593, verified owner marker and process identity. The stop preview bound a plan to the session/process/rootfs/launcher identity; confirmed stop returned stopped=true. Only the process group created by this probe received SIGTERM; no escalation was attempted.
- The temporary registry was removed after stop. Current tx mng proot sessions list is empty. The active Debian session remains visible in proot-distro ps as PID 12830.
- Unit tests also prove malformed registry rejection, symlinked rootfs refusal, and refusal to signal a process without the Ternuxx ownership marker.
- This verifies only the constrained harmless probe lifecycle. Interactive guest login, useful managed Debian workload, GUI, shared display/audio behavior and general production start/stop remain unqualified. The rootfs was used read-only in intent for /bin/sleep; no before/after filesystem hash was captured, so no byte-for-byte rootfs immutability claim is made.
- Legacy db, tx db, x.sh, xgo and killx were not invoked or changed. Floating X11 was not changed.

## API and interface status

- tx mng cron status, start, stop and CLI usage are wired through the shared application service. Scheduler mutations require explicit --yes, and authenticated transport requires cron.scheduler.manage plus its existing CSRF check.
- tx mng proot sessions list/show and proot.status use the shared API and private registry.
- No general PRoot lifecycle action is exposed through API/UI. The test-only probe function is not shown as a generic user action.
- TUI/Web/GTK have not gained scheduler mutation controls in this increment. Their Cron controls remain read-only. No independent lifecycle engine was introduced.
- A read-only pm list packages com.termux.boot attempt returned a package line followed by Android cross-user permission denial; Termux:Boot presence therefore remains unverified. No boot package/configuration was changed.

## Tests and verification

- Focused command: python3 -m unittest tests/test_cron_daemon.py tests/test_cron_scheduler.py tests/test_cron_execution.py tests/test_proot_sessions.py tests/test_management_service.py tests/test_management_sessions.py tests/test_launch_commands.py -q  71 passed, 11.161 seconds, exit 0.
- Full command: bash scripts/repo_test.sh  478 passed, 119.507 seconds, exit 0.
- Also passed: python3 -m compileall -q lib tests; bash -n lib/management.sh; bash -n lib/help.sh; JSON parsing for all 39 schema files; git diff --check; python3 -m tools.repo_knowledge verify (0 findings).
- The CLI invalid-start check tx mng cron start --poll-seconds 5 (without --yes) returned the confirmation message and exit 2 without starting the scheduler.
- Live final read-only status: Cron scheduler stopped, lease not held, dispatch unhealthy/unqualified, 0 jobs and 0 execution records; PRoot Ternuxx session list empty, existing Debian PID 12830 visible.
- No Android reboot, service restart, SSH action, GUI action, Hermes task, production Cron job, Termux:Boot change, unknown listener action, or live existing PRoot-session action occurred.

## Changes in this increment

Implementation:
lib/cron_daemon.py; lib/cron_scheduler.py; lib/cron_registry.py; lib/cron_execution.py; lib/proot_sessions.py; lib/management_service.py; lib/management_authorization.py; lib/management_sessions.py; lib/management.sh; lib/management_catalog.py; lib/help.sh.

Tests:
tests/test_cron_daemon.py; tests/test_cron_scheduler.py; tests/test_cron_execution.py; tests/test_proot_sessions.py; tests/test_management_service.py; tests/test_launch_commands.py.

Documentation:
README.md; CURRENT_STATE.md; docs/architecture/CRON-JOBS.md; docs/architecture/CAPABILITY-MATRIX.md; docs/architecture/MANAGEMENT-API.md; docs/PROOT-SHARED-X11.md; docs/PHASE-STATUS.md (regenerated through the phase workflow).

## Qualification

P3 remains in progress: Cron daemon and harmless isolated dispatch are implemented and tested, but non-default policies, recovery and boot delivery remain unqualified. P4 remains unqualified: the only actual guest lifecycle was the fixed isolated sleep probe; no interactive managed workstation/GUI lifecycle is qualified.
