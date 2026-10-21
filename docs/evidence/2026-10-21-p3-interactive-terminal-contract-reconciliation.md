# P3 interactive terminal contract reconciliation — 2026-10-21

Phase: `P3`

Owner follow-up: the owner subsequently directed that P3 be completed and confirmed before P4 starts. The all-client terminal requirement remains; its broker and Web/GTK transports are staged for P4, not waived. See [the phase-order decision](2026-10-21-p3-before-p4-owner-decision.md).


## Decision and phase boundary

The owner requires interactive PRoot terminal access through CLI, TUI, Web, and GTK. The earlier CLI/TUI-only boundary proposal is withdrawn. The shared broker and the Web/GTK terminal transports are P4 implementation work; P3 records and fixture-checks the ownership and authorization boundary. No client may expose a host shell, caller-selected command/argv, arbitrary rootfs/user/environment, or unrestricted working directory.

The canonical design is [Interactive PRoot terminal architecture](../architecture/INTERACTIVE-PROOT-TERMINALS.md). The capability matrix and P3 roadmap now distinguish the required future all-client capability from currently available behavior: CLI has a process-bound foreground path, the current TUI attached-login route is fixture-tested but not live-qualified, and Web/GTK terminal transports are unavailable.

## Security contract and checks

Web requests continue to reject debian-interactive at the HTTP boundary before dispatch. The shared typed service rejects caller-supplied command, argv, environment, rootfs, user, and working_directory fields. No PTY broker, streaming endpoint, or GTK terminal widget was added.

Verification on Native Termux:

- python3 -m unittest tests.test_management_service tests.test_management_http_runtime tests.test_management_desktop_bridge tests.test_terminal_ui -q — 100 tests passed.
- The HTTP fixture includes an attempted interactive profile request carrying shell/argv/rootfs/user overrides and verifies denial before dispatch.
- The service fixture verifies rejection of arbitrary command, argv, environment, rootfs, user, and working-directory fields.
- These are fixture/source checks, not live terminal qualification.

## Remaining gates and limits

P3 remains in progress. Native cold-boot delivery has not been qualified and requires its own owner-approved Android restart window. Listener-to-port ownership remains unknown because both procfs and NETLINK_SOCK_DIAG observation are denied on this device; the Doctor remains fail-closed. P4 remains planned until the P3 exit audit passes.

No guest was entered; no service, desktop, boot helper, SSH configuration, or Android state was changed. No commit or push was made.

## Evidence

- P3 ownership, parity, and reboot requirements: docs/ROADMAP.md, project/phase-state.json, and the latest P3 gate-review evidence.
- Client boundary: docs/architecture/INTERACTIVE-PROOT-TERMINALS.md and docs/architecture/CAPABILITY-MATRIX.md.
- Fixture coverage: tests/test_management_service.py and tests/test_management_http_runtime.py.
