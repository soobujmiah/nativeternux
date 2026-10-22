# Web PRoot dead-session recovery reconciliation - 2026-10-22

Phase: `P4`
Gate: PARTIAL - one shared recovery action added; full client parity remains open

## Finding and implementation

The shared service already exposed preview and exact-plan reconciliation to CLI, TUI, and GTK, but the authenticated Web adapter returned 403 for the apply operation and the Web UI exposed inspection only.

Web now enables `proot.recovery.reconcile` under the existing `proot.session.manage` capability. The action is available beside the Ternuxx-owned PRoot session picker:

1. The user selects a session with verified Ternuxx ownership.
2. The UI requests a fresh read-only `proot.recovery.reconcile.preview`.
3. Apply is offered only when the preview returns `mark_exited_without_signal`, `confirmation_required=true`, `signal_allowed=false`, and a valid exact plan ID.
4. The user confirms the exact session and observed exit evidence.
5. The API requires CSRF plus a durable idempotency key, then dispatches the same typed management-service operation used by the other clients.
6. The UI refreshes the session list after success.

A live, ambiguous, unreadable, or changed process identity cannot be reconciled. Apply only marks the exact session record stopped after process absence/exit is positively established; it sends no process signal. The ordinary HTTP adapter remains read-only unless the foreground Web runtime is explicitly enabled.

## Native shared-service qualification

The Native 8022 checkout ran a real in-process HTTP adapter flow using `management_service.dispatch` and a private temporary state directory. The fixture contained a synthetic session record pointing at a temporary fixture rootfs and launcher, plus an out-of-range PID confirmed absent. The authenticated API preview returned `process_absent`, action `mark_exited_without_signal`, and `signal_allowed=false`. A CSRF- and idempotency-protected apply changed only that fixture record to `stopped`; response `signal_sent=false`. The record was then re-read from the fixture state.

No existing Debian rootfs, replay guest, host session, or process was targeted. No guest was started and no process signal was sent.

## Checks

- `python3 -m unittest tests.test_management_http_adapter tests.test_management_http_runtime tests.test_management_authorization tests.test_management_sessions tests.test_management_service tests.test_terminal_ui tests.test_management_desktop_bridge -q`: **182 passed, 1 skipped**.
- Full Native `bash scripts/repo_test.sh`: **854 passed, 1 skipped**, 105.351 seconds.
- `python3 -m unittest tests.test_management_http_adapter.ManagementHTTPAdapterTests.test_web_recovery_reconcile_runs_shared_service_on_private_dead_session_fixture -v`: **1 passed**.
- The runtime tests validate the Web inline JavaScript syntax and the preview, apply, ownership, signal, and idempotency controls.
- `git diff --check`: passed.
- Visible Firefox checker was attempted on the existing Native `:1` display with isolated `ternuxx-replay-p4`. Firefox started, but the checker did not observe the synthetic login transition to the catalog within its readiness timeout; it exited before saving screenshots. No UI mutation or managed guest session was started. The new control's visual review remains open.

## Remaining work

This closes only one client-coverage gap. Visible Firefox review on Native X11 `:1` passed for the new control at 742×881: the button rendered inside the action dock and stayed disabled because the read-only session inventory contained zero records. The checker invoked only `management.catalog` and `proot.sessions.list`; no managed session was started or reconciled. The screenshot and successful-run summary are in [visual review evidence](web-reconcile-visual/). Two later checker retries timed out, so repeatable browser-check reliability remains open. Full mutation parity, broader recovery writes, and action-by-action live qualification remain open.

## Evidence

- [P4 next-gate reconciliation](2026-10-22-p4-next-gate-reconciliation.md).
- [P4 phase state](../../project/phase-state.json).
- Source: `lib/management_http_runtime.py`, `lib/management_http_adapter.py`, and `lib/management_web_ui.html`.
- Regression coverage: `tests/test_management_http_adapter.py` and `tests/test_management_http_runtime.py`.
