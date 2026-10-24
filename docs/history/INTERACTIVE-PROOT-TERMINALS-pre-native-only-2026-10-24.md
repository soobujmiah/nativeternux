# Shared interactive PRoot terminals

> **Historical record, superseded 2026-10-24.** Ternuxx is Native Termux-only. PRoot implementation and operations described below have been retired and must not be used as current setup instructions. Current behavior is documented in [the product vision](../PRODUCT-VISION.md), [phase status](../PHASE-STATUS.md), and [Native-only retirement audit](../evidence/2026-10-24-native-only-proot-removal-audit.md).

**Status:** P4 implementation in progress. The Native broker service and CLI/TUI/Web/GTK client paths are implemented. Web uses a locally vendored xterm.js renderer. The installed Management Web UI has now been visually reviewed in Firefox ESR running in the existing Debian PRoot on Native X11 `:1`. A responsive category-navigation defect found in that review is fixed in source. A separate fresh guest has production broker and actual CLI, TUI, Web, GTK/VTE, and sequential cross-client I/O/resize/detach/close evidence; the owner-provisioned `tx db` process remains untouched and is not a Ternuxx-owned test session.

**Owner requirement:** interactive terminal support is required in CLI, TUI, Web, and GTK. Web and GTK use the shared typed broker operations; they may not expose a host shell, arbitrary argv/command, or bypass Android app isolation. See the [P3-first owner decision](../evidence/2026-10-21-p3-before-p4-owner-decision.md).

## Current implementation

- `lib/terminal_broker.py` implements the private Native Unix socket protocol, peer UID checks, bounded frames, generation-bound sessions, one writable attachment, and typed dispatch.
- `lib/terminal_broker.py` (`TerminalPTYRuntime`) owns the preview-bound fixed `debian-interactive` PTY, bounds input/output and resize, and fails closed on uncertain session identity. It does not adopt pre-existing PRoot processes.
- `scripts/termux-services/ternuxx-terminal-broker/run` and `lib/terminal_service_deployment.py` provide a preview-first Runit service. Live status reported `ok: true` and `pty_relay: not_connected`; no guest was started by that status check.
- `tx terminal` provides service/status/start/attach/close operations. TUI and GTK/VTE use the shared terminal client path. The GTK app is installed in the desktop app list; its installed source identity was verified against `apps/management-center/management-center.c` in the prior GUI review.
- `lib/management_web_ui.html` implements previewed start/close, managed-session selection, single-use channel issuance, attach/detach, resize, and bounded output polling using vendored xterm.js and FitAddon. The HTTP adapter applies the Web session, CSRF, exact-origin, channel-ticket, session-ID, and broker-generation checks.
- Opening the management page does not start a guest. A new managed interactive session requires explicit review and confirmation of the exact plan. Closing likewise uses a fresh exact-session preview.

## Safety boundaries

Only the fixed `debian-interactive` profile can be started. Terminal clients cannot choose a command, argv, rootfs, guest user, environment, working directory, or guest alias. The Native service operator may select `debian` (default) or an explicit `ternuxx-replay-NAME` at service startup. Discovery, preflight, the preview plan and launcher all use that same selected rootfs; there is no fallback to the working guest. Rootfs/launcher inode checks remain mandatory. The broker does not adopt an existing process. Detach only releases the client channel; close is separately previewed and confirmed. Terminal content is not persisted or written to logs. Broker restart cannot claim that a live process is reattachable when its PTY master is gone; uncertain records remain unknown. The owner-reported `tx db` process is protected and has not been entered or changed for this review.

## Review and verification

The 2026-10-22 Native Termux implementation passed the full 700-test suite, focused broker/Web/runtime checks, Python compilation, repository knowledge verification, and `git diff --check`; see [persistent broker and Web terminal evidence](../evidence/2026-10-22-p4-persistent-broker-web-terminal.md). Earlier GTK and broker checks are in [terminal client and GUI evidence](../evidence/2026-10-22-p4-terminal-client-and-gui-review.md).

The initial 752x1124 visual review exposed category labels crossing into the resource column and a later reload lost its consumed bootstrap credential. Those failures remain historical evidence. The later [Native UI review](../evidence/2026-10-22-native-ui-and-audit-remediation.md) records authenticated responsive checks at exact 390/752/1440 CSS-pixel widths and a visible Firefox run on Native X11. It verifies action stability and the terminal dialog/renderer using session-inventory reads; it does not qualify guest terminal I/O.

## Separate guest qualification

The broker's default remains the existing Debian guest. To qualify the same production assembly against a separate freshly installed guest, start a second foreground broker in a distinct private state namespace:

```sh
mkdir -m 700 "$HOME/.local/share/ternuxx-terminal-replay"
TERNUXX_STATE_DIR="$HOME/.local/share/ternuxx-terminal-replay" \
  python3 lib/terminal_broker_service.py serve --guest-alias ternuxx-replay-p4
```

Run this from the Native source checkout only after the new guest setup finishes and its ordinary `sbj` account exists. Use that exact `TERNUXX_STATE_DIR` for qualification clients as well. Do not restart/reconfigure the existing broker or point this namespace at the working Codex guest. The service argument selects a validated container name, never a filesystem path or arbitrary command. Preview identifies the selected alias/rootfs and its login-time profile side effects before explicit apply. Detach and close keep their existing ownership checks.

[Guest selection evidence](../evidence/2026-10-22-terminal-guest-selection.md) distinguishes assembly/regression checks from live lifecycle acceptance.

## Remaining P4 acceptance

1. Retain the [completed separate setup and broker/client evidence](../evidence/2026-10-22-fresh-setup-and-probe-safety.md); exact replay-guest retirement/restore is verified, while broader config replay and graphics workload acceptance remain open.
2. Retain completed CLI, TUI, Web and GTK/VTE lifecycle and sequential cross-client handoff evidence. [Cross-client evidence](../evidence/2026-10-22-cross-client-terminal-handoff.md) records exact start, I/O, resize, detach and close.
3. Recheck attachment ownership and close behavior under failure/concurrency. Opening the terminal dialog is not an I/O pass. [Web replay](../evidence/2026-10-22-web-terminal-replay.md) covers actual Firefox I/O and viewport-to-guest resize.
4. Keep P4 in progress until the remaining provider/configuration, clean-device/full-workstation reproducibility, and preservation criteria pass. Visible Firefox layout/control review passed for its recorded scope; full Web mutation/client parity remains open. Update evidence and roadmap from observed results.

## Legacy Ternux CLI retirement

On 2026-10-22, the old Native Ternux command and Debian guest companion were retired only after the current Ternuxx CLI and fixed guest verifier were exercised. Both retirements used exact previews and private same-filesystem backups without signaling PRoot. Rollback details are in the [runtime and legacy CLI follow-up](../evidence/2026-10-22-p4-legacy-cli-and-runtime-recheck.md). Historical prior-name recovery compatibility is documented at that checkpoint.
