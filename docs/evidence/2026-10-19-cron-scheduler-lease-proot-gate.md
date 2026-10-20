Phase: `P3`
# Cron scheduler lease and PRoot ownership gate - 2026-10-19

## Baseline and scope

Implemented and validated in the Native Termux repository at $HOME/ternuxx through the existing local SSH 8022 development connection. Branch main; starting HEAD 69e378eb33247678437bda4b2de9ab25f6bcb91d. Worktree had 153 status entries at the start; no reset, clean, stash, commit, or push occurred. At final evidence capture the count was 156 (three new untracked source, test, and evidence files); all pre-existing dirty changes were preserved.

Native runtime observed: HOME=/data/data/com.termux/files/home; PREFIX=/data/data/com.termux/files/usr. The Debian distribution is installed and the configured rootfs path under PREFIX/var/lib/proot-distro/containers/debian/rootfs exists. The read-only proot.status response still reports host PRoot process ownership unverified and guest_entered=false. PID 12830 was visible in the status snapshot but was not signalled or modified. The floating X11 GUI was not touched.

## Implemented

- Added lib/cron_scheduler.py with an isolated advisory-lock singleton lease, private atomic scheduler instance metadata, PID start-time identity checks, heartbeat, fail-closed malformed/symlink state handling, a lease-guarded single-event dispatch primitive, and stable event IDs based on job ID plus normalized UTC due instant.
- Reused cron_execution.claim_event and execute_claimed. Duplicate event identity returns the existing ledger record; disabled jobs remain skipped. No second job registry or execution ledger was introduced.
- Added the fixed no-side-effect action scheduler.self_test and mapped it to cron.executor.self_test under diagnostics.read. It accepts no parameters and executes no command supplied by a caller.
- Added tests/test_cron_scheduler.py: singleton contention, private state, duplicate event dispatch, disabled-job suppression, malformed/symlink state refusal, and the real registered subprocess runner.

## Execution semantics and limits

The lease/dispatch core is not a resident daemon. No due-event polling loop, production scheduler start/stop, service unit, retry engine, pending queue, cancellation, automatic missed-run handling, boot-event source, or scheduler-recovery event delivery was implemented or enabled. The status API remains scheduler=not_installed, process=not_running, execution=core_available_no_scheduler. A held lease is not evidence that schedule polling is healthy.

Atomic claims suppress duplicate event claims, not arbitrary exactly-once side effects. If a process crashes after action effects but before completion is committed, the execution remains uncertain and is not retried automatically. Retry policies above one attempt and queue_one remain rejected by the execution core. Boot/recovery triggers remain unqualified.

The real subprocess test used the harmless registered scheduler.self_test action inside temporary state. It returned succeeded and recorded a bounded result. No production job definition or state was read for execution, and no live scheduler was started.

## PRoot status

No PRoot lifecycle code or API mutation was added. Native tx mng proot status remains read-only and reports Debian installed, host PRoot process ownership unverified, and guest_entered=false. No rootfs content was modified, no guest was entered, and no start/stop preview or lifecycle action was issued. Start/stop remain unavailable until Ternuxx can create a separately tagged session and revalidate the durable instance token and process start identity before signalling that exact child. Shared rootfs path is not ownership proof.

Legacy db, x.sh, xgo, killx, tx db, active Codex session, X11, SSH, Hermes, boot configuration, and services were not changed.

## Evidence

P3 evidence record.

## Verification

- python3 -m unittest tests/test_cron_scheduler.py -v: 7 tests passed; exit 0.
- python3 -m unittest tests/test_cron_registry.py tests/test_cron_execution.py tests/test_cron_scheduler.py tests/test_management_service.py tests/test_management_authorization.py -v: 65 tests passed in 1.359 seconds; exit 0.
- python3 -m unittest tests/test_management_sessions.py tests/test_cron_scheduler.py -q: 15 tests passed; exit 0.
- bash scripts/repo_test.sh: 471 tests passed in 78.950 seconds; exit 0.
- python3 -m compileall -q lib tests: exit 0.
- JSON parse of 39 schema files: exit 0.
- bash -n lib/management.sh: exit 0.
- git diff --check: exit 0.
- python3 -m tools.repo_knowledge verify: 0 findings; exit 0.
- Read-only native tx mng cron status: scheduler not_installed, no production executions, zero registry/ledger records.
- Read-only native tx mng proot status: Debian installed, process visibility complete for observed entries, ownership unverified, guest_entered=false.

An initial full-suite run caught the new read-only action missing from the explicit HTTP-session operation classification (469 passed, one failed). The operation was classified under diagnostics.read; the focused authorization/session tests and final 470-test full suite then passed.

## Phase status and rollback

P3 remains in progress. Cron lease and isolated dispatch are fixture/controlled-action tested; production scheduler and trigger delivery are unqualified. P4 remains unqualified because no Ternuxx-owned PRoot session lifecycle or guest workload parity was tested. No startup configuration or installed artifact was changed, so rollback is limited to reverting only the new scheduler source/test and this increment's documented references if later required; preserve unrelated worktree changes.
