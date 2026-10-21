# P4 terminal client and GUI review - 2026-10-22

## Scope

Phase: `P4`

This is incremental P4 evidence; it does not claim phase completion.

Work was implemented and exercised through Native Termux over the owner-started SSH 8022 repository shell. The existing Debian rootfs and live PRoot session were left untouched. The owner confirmed that the current PRoot candidate was started using tx db and is the session used for Codex work. This provenance is owner-reported: current tx db source calls proot-distro login directly and does not persist a Ternuxx session record.

## Visual inspection

The owner reported Termux:X11 floating. Native display :1 had stale session state, so its exact Ternuxx-owned startup path was invoked for the requested GUI inspection. The GTK Management Center was inspected from Native X11 screenshots. The category/resource/detail layout now uses a wider category pane and vertically split resource/detail sections. The PRoot action list was initially clipped; it now has its own scroll area, and Open Debian terminal is reachable by scrolling. GTK 4.24.1 and VTE 0.84.1 were present. The rebuilt installed GTK client identity records a source SHA-256 equal to apps/management-center/management-center.c. No Android Activity was launched.

## Broker implementation and smoke check

Source now includes a Native fixed-profile PTY broker service assembly, bounded Unix-socket server loop, tx terminal CLI, TUI broker attach path, and GTK/VTE terminal launcher. The GTK launcher does not start a guest until the user confirms the exact preview in the terminal client.

The foreground broker was started without a guest session. tx terminal status and the shared management status operation both returned success, generation identity, and pty_relay=not_connected. The foreground server was then interrupted and the socket became unavailable. No PRoot start/stop operation was issued.

Focused TUI tests passed 31/31. The full Native Termux repository suite passed 687/687 in 98.799 seconds. Python bytecode compilation and git diff --check passed. Repository knowledge verification reported zero findings.

## Evidence

- Native Termux suite: 687/687 passed.
- Focused TUI suite: 31/31 passed.
- GUI screenshots visibly confirmed the scrollable PRoot action list and reachable terminal action.
- Installed GTK identity source hash matches the current C source.
- Broker status smoke checks passed without starting a PRoot login.

## Remaining P4 gates

- Broker is a manually launched foreground service; no Runit-managed persistent deployment exists yet.
- Web transport still rejects interactive PRoot login and has no browser terminal renderer or terminal operation scopes.
- Four-client interactive terminal parity is incomplete; CLI/TUI/GTK source is present, but only the no-guest broker status path was exercised live.
- The current tx db source does not register its login in the Ternuxx PRoot session registry. The owner confirmed provenance, but machine-level identity/ownership remains unverified. The live process and rootfs were not changed.
- A live terminal login was intentionally not started because it would create a new guest session. P4 remains in progress.

## Preservation

The existing PRoot process/rootfs, existing db launcher behavior, SSH 8022/8023 configuration, and user files were not modified by this review. Native X11 :1 is running after the requested GUI review.
