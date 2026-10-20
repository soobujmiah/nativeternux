# P3 PRoot session client implementation — 2026-10-21

Phase: `P3`

## Evidence



The existing shared typed service now backs PRoot session management in the TUI and Web client. Both can list sessions, inspect per-session recovery state, preview and apply only the fixed `isolated-probe` profile (300 seconds), and request stop only after a fresh preview verifies Ternuxx ownership and binds the exact session ID to the plan. The TUI requires an explicit confirmation. Web requires its existing authenticated session, CSRF protection, idempotency key, and explicit browser confirmation; the HTTP adapter rejects all other PRoot start profiles and explicitly blocks recovery reconciliation.

The bridge validates session IDs and full plan IDs before dispatch. Tests cover TUI plan binding, refusal to stop unverified sessions, Web fixed-profile acceptance, interactive-profile refusal, session stop dispatch, existing request guards, and bridge validation.

## Checks

- Native Termux focused suite: `python3 -m unittest tests.test_terminal_ui tests.test_management_http_runtime tests.test_management_http_adapter tests.test_management_desktop_bridge tests.test_management_authorization -q` — 80 passed.
- `git diff --check` — passed before the documentation update.
- GTK source was not changed or visually exercised in this increment. GTK still lacks session list/recovery/probe/stop controls, so the cross-client parity gate remains open.
- No live PRoot probe was started or stopped. No existing Debian session, native GUI, managed GUI, or SSH service was restarted.

## Remaining P3 gates

GTK parity and visual qualification remain open. Live `debian-interactive` remains blocked by the existing fail-closed TTY/guest identity result; do not retry without a supported terminal transport. TCP ownership evidence and cold-boot delivery qualification remain separate P3 gates. P3 remains active.
