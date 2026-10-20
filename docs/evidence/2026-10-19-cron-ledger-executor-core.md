Phase: `P3`

# Cron ledger and typed executor core — 2026-10-19

## Repository and baseline

Implementation ran in Native Termux over the existing manually managed SSH 8022 development path, repository $HOME/ternuxx. Branch main, HEAD 69e378eb33247678437bda4b2de9ab25f6bcb91d. At initial inspection the worktree had 149 status entries; all were preserved. No commit was created. Three implementation files were added in this increment (execution core, tests, schema); final status entry count was 152. The installed tx route points to the checkout through the existing shim and source code; no deployment or package installation was performed.

The existing v1 typed registry, four schedule types, timezone adapter and policy validation were retained. Read-only process inspection did not identify a Ternuxx Cron daemon; the matching process scan only returned the SSH/inspection command itself. Native Cron status showed an empty registry and no scheduler. Existing running services/sessions were not controlled.

## Implemented

- Added lib/cron_execution.py with schema-v1 private execution ledger at $TERNUXX_STATE_DIR/cron/executions.json, sharing the existing Cron directory and mutation lock.
- Event claim records have stable execution/event/job/scheduler-instance identities; claim and job mutations serialize through the existing lock. Repeated event claims return the original record. Disabled and unauthorized boot/recovery trigger events are persisted as skipped. One-time jobs do not execute again after a terminal attempt.
- skip_overlap records a skipped event. queue_one fails explicitly because there is no persistent worker queue. Jobs configured for more than one retry attempt are refused until retry dispatch exists.
- Added a fixed typed action map for three read-only management actions. No user command string or shell field is accepted. The runner uses a new process group, timeout, bounded pipe capture, private output summaries and secret-pattern redaction. It verifies the launched process start identity and group leader before signaling on timeout.
- A crash that leaves an event claimed or running remains unresolved and blocks overlapping claims. It is not automatically rerun. The ledger does not promise exactly-once external side effects across the crash gap between action completion and result persistence.
- Added schema schemas/cron-execution-v1.schema.json, bounded read-only shared API operations cron.executions.list/show, and CLI tx mng cron executions list/show. Read access uses the existing diagnostics.read scope. No API run/cancel or scheduler start/stop operation was added.
- Cron status distinguishes core_available_no_scheduler; the resident scheduler remains not_installed. The catalog and capability matrix distinguish the ledger core from scheduler/boot delivery.

## Evidence

## Verification

Commands executed in Native Termux:

- python3 -m unittest tests.test_cron_execution tests.test_cron_registry tests.test_management_service tests.test_management_catalog tests.test_management_authorization tests.test_management_sessions tests.test_management_http_adapter tests.test_management_http_runtime -q — 95 tests passed, 1.379 s, exit 0.
- bash scripts/repo_test.sh — 464 tests passed, 82.567 s, exit 0.
- python3 -m py_compile lib/cron_execution.py lib/management_service.py — passed.
- python3 -m compileall -q lib tests — passed.
- bash -n lib/management.sh — passed.
- JSON parsing of Cron job and execution ledger schemas — passed.
- git diff --check — passed.
- python3 -m tools.repo_knowledge verify — zero findings, exit 0.
- Live read-only tx mng cron status — empty job registry and ledger; scheduler=not_installed, process=not_running, execution=core_available_no_scheduler, boot delivery=not_qualified, recovery delivery=not_installed.
- Live read-only tx mng cron executions list — empty array, exit 0.

Execution outcome transitions, disabled-job suppression, duplicate claims, overlap handling, bounded/redacted output, simulated failure/timeout, corrupt ledger refusal and API history were tested using temporary state and injected fake executors. The production subprocess action path was not invoked. There was no live job execution or scheduler process.

## Not implemented or unqualified

No resident scheduler singleton/lease lifecycle, automatic due-event scanner, job retry/backoff, queue_one worker queue, execution cancellation, unresolved-running recovery, missed-run/catch-up implementation, Android device-boot adapter, scheduler-recovery event delivery, production API execution endpoint, or TUI/Web/GTK history view. The validated retry/missed-run settings do not imply operational behavior. The fixture path proves ledger transitions only. The production action subprocess and timeout signal path remain unqualified on-device.

No reboot, boot integration, Cron job, service, listener, GUI, Debian PRoot session, Hermes task, or SSH operation was started, stopped, signaled, or changed. Ports 8022, 8023 and 8765 were not altered. Active Codex and GUI sessions were left untouched.

P3 remains in progress. P4 remains unqualified. No rollback is required; the change is source/schema/test/docs only and has not been installed as a service.
