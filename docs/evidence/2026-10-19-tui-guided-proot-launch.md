# Guided PRoot app launch in TUI — 2026-10-19

## Implementation

The Native Termux `tx tui` client now offers `l=PRoot app`. It asks for an ID from the existing named PRoot application catalog, lets the user choose the `ternuxx` or `ternux` X11 session, validates an optional `:N` display, requires an explicit display for the `ternux` session, and asks for confirmation before dispatching `proot.app.launch` through the shared management service. It does not accept shell commands or add a second launch implementation.

The existing Ternux session remains the owner of its desktop and rootfs. This TUI action requests only a named application through the existing adapter; it does not start or stop a desktop, edit the guest, install packages, or change the rootfs.

## Verification

- Focused Native Termux TUI tests: 10/10 passed.
- Full Native Termux repository suite: 346/346 passed in 82.494 seconds.
- Tests cover session/display routing, required Ternux display, malformed display rejection, unknown app IDs, and cancellation before dispatch.
- No live PRoot app launch was requested during verification. No guest entry or device lifecycle action occurred.

## Limits

This is a guided TUI path to the existing shared operation. It does not complete browser mutations, general Graphical UI management, live provider ownership, or P4 workload parity. P3 remains active and P4 remains planned.
