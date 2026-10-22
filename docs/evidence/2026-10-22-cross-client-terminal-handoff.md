# Cross-client terminal handoff — 2026-10-22

Phase: `P4`

## Evidence

## Result

**PASS for the named sequence:** a single receipt-verified `ternuxx-replay-p4` session was started and used through the real CLI, detached, attached through the authenticated Web terminal API, detached, then attached through the real TUI and detached. Each client exchanged a unique guest output marker and verified terminal resize from inside the guest. The same running session ID stayed visible in the shared management inventory and GTK terminal-picker bridge. The exact replay session was then closed through preview and confirmation and recorded `stopped`/`released`.

- Session: `proot-28e73c176ae244d29d36f103ea812688`
- Command: `"$HOME/.cache/ternuxx-ui-check-venv/bin/python" tools/check_terminal_handoff.py --alias ternuxx-replay-p4`
- Runtime: Native Termux over the configured repository SSH 8022 channel.
- Target rootfs identity was validated from the private setup receipt before launch.
- Default Debian rootfs device/inode and `etc/profile.d/termux-profile.sh` SHA-256 were unchanged.
- The private broker, guest session, and private state directory were stopped/released and removed after PASS.
- The pre-existing PRoot PID with unverified ownership was not signaled or adopted.

The checker’s alias guard was also exercised with `--alias debian`; it rejected the protected default target with argparse exit 2 before any live guest operation. Python bytecode compilation and `--help` passed; the protected-default alias and a path-traversal alias both exited 2 as expected. The full Native repository suite passed 834/834 in 95.433 seconds.

## Scope limit

This proves CLI → authenticated Web API → TUI continuity and that the GTK picker data source sees the shared session. It does **not** prove attach/I/O continuity through the GTK/VTE window itself, the browser-rendered Web terminal UI, graphics workload parity, replay guest retirement/rollback, or the remaining P4 acceptance matrix. Existing separate per-client lifecycle evidence remains applicable only to its recorded scope.

Terminal command/output contents were not saved; only unique marker success, geometry checks, session identity, cleanup, and preservation results were recorded.
