# P3 PRoot session client implementation — 2026-10-21

Phase: `P3`

## Evidence



The existing shared typed service now backs PRoot session management in the TUI and Web client. Both can list sessions, inspect per-session recovery state, preview and apply only the fixed `isolated-probe` profile (300 seconds), and request stop only after a fresh preview verifies Ternuxx ownership and binds the exact session ID to the plan. The TUI requires an explicit confirmation. Web requires its existing authenticated session, CSRF protection, idempotency key, and explicit browser confirmation; the HTTP adapter rejects all other PRoot start profiles and explicitly blocks recovery reconciliation.

The bridge validates session IDs and full plan IDs before dispatch. Tests cover TUI plan binding, refusal to stop unverified sessions, Web fixed-profile acceptance, interactive-profile refusal, session stop dispatch, existing request guards, and bridge validation.

## Checks

- Native Termux focused suite: `python3 -m unittest tests.test_terminal_ui tests.test_management_http_runtime tests.test_management_http_adapter tests.test_management_desktop_bridge tests.test_management_authorization -q` — 80 passed.
- Full Native Termux repository suite: `bash scripts/repo_test.sh` — 646 passed in 106.676 seconds.
- `git diff --check` — passed.
- GTK now exposes session inventory and recovery reads, fixed-probe preview/apply with confirmation, and exact-session stop after the bridge verifies ownership and the exact plan. `clang -O2 -Wall -Wextra -fsyntax-only apps/management-center/management-center.c $(pkg-config --cflags gtk4)` passed. `bash scripts/install-management-center.sh` installed the updated binary and launcher after the script verified the previous install identity. Installed binary SHA-256 is `db14421132be355e1d23bd58f110cd3aaaa4d52e5e2bc2df697ffbe0cde6aea8`; identity records source C SHA-256 `83bfd7e0e0b82e5aac360341eb3b54030c8858999633393464272b4176a193e8` and bridge SHA-256 `60349c473fbe8309f5ec82e762ef7d31ed69d31de279bac215b7b507f17a35ac`. The existing GTK window was not restarted, so it continues running its already-loaded binary; visual/live interaction remains unqualified. New launches use the installed update.
- No live PRoot probe was started or stopped. No existing Debian session, native GUI, managed GUI, or SSH service was restarted.

## Remaining P3 gates

GTK source parity is implemented and compiles; visual/manual qualification remains open. Live `debian-interactive` remains blocked by the existing fail-closed TTY/guest identity result; do not retry without a supported terminal transport. TCP ownership evidence and cold-boot delivery qualification remain separate P3 gates. P3 remains active.
