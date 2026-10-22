# Cross-client terminal handoff — 2026-10-22

Phase: `P4`

## Evidence

## Result

**PASS for the named sequence:** a single receipt-verified `ternuxx-replay-p4` session was started through the real CLI, then detached and attached through the authenticated Web terminal API, TUI, and installed GTK/VTE client in sequence. Each client exchanged a unique guest output marker and exercised terminal resize from inside the guest. The same session ID stayed visible in shared management inventory and the GTK picker bridge. GTK/VTE detached with Ctrl-], the session remained available, and the exact replay session was then closed through preview and confirmation and recorded `stopped`/`released`. See the [GTK/VTE live evidence](2026-10-22-gtk-vte-same-session.md) and [focused VTE screenshot](2026-10-22-gtk-vte-same-session.png).

- Session: `proot-bbed88095bd149bfb5aad1d8da33b92d`
- Command: `DISPLAY=:1 "$HOME/.cache/ternuxx-ui-check-venv/bin/python" tools/check_terminal_handoff.py --alias ternuxx-replay-p4 --gtk-display :1 --gtk-screenshot docs/evidence/2026-10-22-gtk-vte-same-session.png`
- Runtime: Native Termux over the configured repository SSH 8022 channel.
- Target rootfs identity was validated from the private setup receipt before launch.
- Default Debian rootfs device/inode and `etc/profile.d/termux-profile.sh` SHA-256 were unchanged.
- The private broker, guest session, and private state directory were stopped/released and removed after PASS.
- The pre-existing PRoot PID with unverified ownership was not signaled or adopted.

The checker’s alias guard was also exercised with `--alias debian`; it rejected the protected default target with argparse exit 2 before any live guest operation. Python bytecode compilation and `--help` passed; the protected-default alias and a path-traversal alias both exited 2 as expected. The full Native repository suite after the four-client handoff and scoped GTK test-instance cleanup passed 847/847 in 99.597 seconds.

## Scope limit

This proves same-session attach/I/O continuity through CLI, authenticated Web API, TUI, and GTK/VTE. It does **not** prove browser-rendered Web terminal controls, graphics workload parity, GTK replay-guest retirement apply, or the remaining P4 acceptance matrix. Existing per-client lifecycle evidence remains applicable only to its recorded scope.

The focused GTK/VTE screenshot is the only retained guest-output view; the other clients' terminal output and all private broker/session state were discarded after marker, resize, cleanup, and preservation checks.
