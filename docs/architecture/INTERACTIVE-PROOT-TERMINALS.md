# Shared interactive PRoot terminals

**Status:** P4 implementation in progress. The Native broker service and CLI/TUI/Web/GTK client paths are implemented. Web uses a locally vendored xterm.js renderer. The installed Management Web UI has now been visually reviewed in Firefox ESR running in the existing Debian PRoot on Native X11 `:1`. A responsive category-navigation defect found in that review is fixed in source. A managed guest attach has not been live-qualified; the owner-provisioned `tx db` process remains untouched and is not a Ternuxx-owned test session.

**Owner requirement:** interactive terminal support is required in CLI, TUI, Web, and GTK. Web and GTK use the shared typed broker operations; they may not expose a host shell, arbitrary argv/command, or bypass Android app isolation. See the [P3-first owner decision](../evidence/2026-10-21-p3-before-p4-owner-decision.md).

## Current implementation

- `lib/terminal_broker.py` implements the private Native Unix socket protocol, peer UID checks, bounded frames, generation-bound sessions, one writable attachment, and typed dispatch.
- `lib/terminal_pty_runtime.py` owns the preview-bound fixed `debian-interactive` PTY, bounds input/output and resize, and fails closed on uncertain session identity. It does not adopt pre-existing PRoot processes.
- `scripts/termux-services/ternuxx-terminal-broker/run` and `lib/terminal_service_deployment.py` provide a preview-first Runit service. Live status reported `ok: true` and `pty_relay: not_connected`; no guest was started by that status check.
- `tx terminal` provides service/status/start/attach/close operations. TUI and GTK/VTE use the shared terminal client path. The GTK app is installed in the desktop app list; its installed source identity was verified against `apps/management-center/management-center.c` in the prior GUI review.
- `lib/management_web_ui.html` implements previewed start/close, managed-session selection, single-use channel issuance, attach/detach, resize, and bounded output polling using vendored xterm.js and FitAddon. The HTTP adapter applies the Web session, CSRF, exact-origin, channel-ticket, session-ID, and broker-generation checks.
- Opening the management page does not start a guest. A new managed interactive session requires explicit review and confirmation of the exact plan. Closing likewise uses a fresh exact-session preview.

## Safety boundaries

Only the fixed `debian-interactive` profile can be started. Callers cannot choose a command, argv, rootfs, guest user, environment, or working directory. The broker does not adopt an existing process. Detach only releases the client channel; close is separately previewed and confirmed. Terminal content is not persisted or written to logs. Broker restart cannot claim that a live process is reattachable when its PTY master is gone; uncertain records remain unknown. The owner-reported `tx db` process is protected and has not been entered or changed for this review.

## Review and verification

The 2026-10-22 Native Termux implementation passed the full 700-test suite, focused broker/Web/runtime checks, Python compilation, repository knowledge verification, and `git diff --check`; see [persistent broker and Web terminal evidence](../evidence/2026-10-22-p4-persistent-broker-web-terminal.md). Earlier GTK and broker checks are in [terminal client and GUI evidence](../evidence/2026-10-22-p4-terminal-client-and-gui-review.md).

The current visual review opened the authenticated UI in Firefox ESR over Native X11 `:1`. The pre-fix 752x1124 capture showed long numbered category labels crossing into the resource column. The navigation buttons now wrap within the category column and the two-column responsive grid uses a zero-minimum content column in source. The Web terminal is present in the Debian workloads resource action. The authenticated pre-fix page was reviewed; the post-fix reload rejected the one-time credential, so a post-fix authenticated screenshot is still needed. No guest was attached or started.

## Remaining P4 acceptance

1. Run focused Web/runtime tests after the responsive CSS and help changes; run the full suite if those checks expose shared behavior changes.
2. Repeat the browser visual check against the patched page and record the post-fix result.
3. Qualify start, attach, input/output, resize, detach, and exact close with a disposable Ternuxx-managed test guest. Do not use the existing `tx db` process as the test guest.
4. Verify the same end-to-end lifecycle in CLI, TUI, and GTK/VTE against that isolated session, then update phase evidence and the roadmap. P4 stays in progress until these gates pass.

## Legacy Ternux CLI retirement

On 2026-10-22, the old Native Ternux command and Debian guest companion were retired only after the current Ternuxx CLI and fixed guest verifier were exercised. Both retirements used exact previews and private same-filesystem backups without signaling PRoot. Rollback details are in the [runtime and legacy CLI follow-up](../evidence/2026-10-22-p4-legacy-cli-and-runtime-recheck.md). Historical prior-name recovery compatibility is documented at that checkpoint.
