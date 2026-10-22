# Native TUI terminal replay — 2026-10-22

Phase: `P4` in progress. Target: separate, setup-receipted `ternuxx-replay-p4` guest.

The actual Native `./tx tui` process was exercised through a private pseudo-terminal and a private production broker. Guided menu navigation and start preview/confirmation led to a verified owned Debian session. The guest returned a unique I/O marker and observed the resized 28 × 95 terminal. Ctrl+] detached without closing the guest; the TUI session picker reattached the same terminal, returned a second guest marker, detached again, displayed an exact stop preview with SIGHUP, confirmed closure, and exited cleanly. [Machine-readable result](2026-10-22-tui-terminal-live.json).

The checker uses an in-memory terminal screen model because curses sends incremental cell updates. No terminal content, credentials, broker tokens or private state were committed. The first replay reached stop preview but its exact `SIGHUP` expectation exposed that the human presenter changed the signal name to `Sighup`. The presenter now keeps POSIX signal names uppercase; after exact owned-session recovery and private broker cleanup, the full replay passed. A previous raw-byte matcher failed before guest start and was replaced with screen reconstruction.

The checker validates a completed separately owned setup receipt and rootfs identity, and captures the working Debian root identity plus its selected generated-profile hash before/after. Its successful run removed its private broker/state; no test session remained. The result is scoped to that target and those preservation checks. It does not prove pixel appearance, performance, Web/GTK terminal lifecycle, full working-rootfs immutability, or fresh removal/rollback.

## Evidence

Source checks: the final full Native suite passed 749/749 in 99.054 seconds after the signal-presenter correction; the affected TUI/presenter unit module passed 44/44. [Source-bound suite result](2026-10-22-tui-source-regression.json). The final replay also passed from the pinned isolated checker venv after replacing its preservation assertions with explicit runtime checks. The optional replay checker is `tools/check_tui_terminal.py`; its pinned terminal model dependencies are in `tools/requirements-tui-replay.txt`. It is an opt-in live device check, not part of ordinary CI.

Next: qualify actual Web and GTK terminal flows on the same separate guest, then continue the wider P4 and repository audit work.
