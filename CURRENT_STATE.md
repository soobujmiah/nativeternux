# Current Ternuxx handoff

Git/CI facts belong to [generated status](.repo/STATUS.md); phase acceptance belongs to [phase state](project/phase-state.json). Earlier snapshots are preserved in [dated history](docs/handoff/2026-10-22-current-state-history.md).

## Product and execution boundary

Native Termux owns boot/recovery, SSH, CLI, management, state, and native workloads. Debian PRoot is an optional provider. The four clients share typed services but still have different action coverage. See [product vision](docs/PRODUCT-VISION.md), [architecture](docs/ARCHITECTURE.md), and [client coverage](docs/architecture/CAPABILITY-MATRIX.md).

Implement in Native `$HOME/ternuxx` over SSH 8022. The installed `tx` shim dispatches to this checkout. Port 8023 is the separate managed product service. Preserve both channels, Native Termux, and the owner's active Codex PRoot session. This task authorizes bounded development, required installs, GUI review, and reversible PRoot configuration work; it does not authorize replacing/pruning the existing rootfs or shutting down the workstation.

## Phase and qualification

P0–P3 are recorded complete within dated evidence scope; P4 remains active. [P3 RB08 evidence](docs/evidence/2026-10-22-p3-rb08-postboot-exit-audit.md) distinguishes observed Native boot/authenticated readiness from its private NOT_READY checkpoint. The current recovery module copy was deployed after that boot; its later cold-boot execution is unobserved. No reboot is part of this continuation.

The persistent Native terminal broker and CLI/TUI/Web/GTK paths exist. Actual CLI, TUI and authenticated Web terminal lifecycle passed on the separate replay guest. GTK terminal lifecycle and cross-client continuity remain open. The owner's `tx db` process must not be used as that lifecycle test target.

## Latest implementation

Web now has purpose-ordered numbered categories, actions before independently scrolling details, concise summaries, explicit unauthenticated hidden state, and mobile/tablet quick controls bound to real selected-resource actions. Web/TUI/GTK consume one category order.

Browser menu Auto selection and failed code-handoff handling are repaired. The clipboard-failure fixture now explicitly selects Android; a literal escape preventing the terminal-service test module from loading is fixed. The opt-in [Firefox checker](tools/check_web_ui.py) verifies authentication, search, overflow, action stability, the external 8022 boundary, and the terminal dialog using catalog/session-inventory reads only.

GTK was rebuilt and source/bridge/binary identities match. All three checked-in Runit definitions, all three boot helpers, tx shim and the three installed canonical recovery modules match source; isolated recovery imports resolve from the installed path. See the [entrypoint inventory](docs/evidence/2026-10-22-native-entrypoint-inventory.json). The fixed GUI monitor scheduler is now installed and running idle; monitoring/focus/Activity launch remain off. Fresh registration and two 30-second Linux-only ticks passed in a separate private Runit root. CLI service registration is available; shared-client install controls remain open. This is partial live/source parity, not a completed audit of every installed component. See [UI/audit evidence](docs/evidence/2026-10-22-native-ui-and-audit-remediation.md) and [monitor deployment/replay](docs/evidence/2026-10-22-monitor-service-registration.md).

The separate `ternuxx-replay-p4` setup completed: 54 requested packages, account/locale, installed inventory and pinned Turnip hash verified. Working Debian root identity and selected protected-file hashes were preserved. The production broker and actual CLI I/O/resize/detach/reattach/exact close passed on this new guest after live stop defects were fixed. GTK lifecycle, cross-client continuity, graphics workload and rollback remain open. [Fresh setup and probe safety](docs/evidence/2026-10-22-fresh-setup-and-probe-safety.md) records 743 passing Native tests and scope limits.

Actual Native TUI guided start, guest I/O/resize, detach, reattach and preview-confirmed exact close passed on the separate guest. The menu now scrolls all actions and uses an owned-session picker; POSIX signal names remain uppercase in human reports. [TUI replay evidence](docs/evidence/2026-10-22-tui-terminal-replay.md).

Real Firefox Web terminal start, guest I/O/resize, detach, reattach and exact close passed on the separate guest after a 63-bit generation transport fix. [Web replay evidence](docs/evidence/2026-10-22-web-terminal-replay.md).

Guest probes now disclose launcher profile writes and require control scope/CSRF over HTTP. Debian graphics status and browser detection no longer enter the guest. New loopback runtimes passed live authorization/status checks; existing Web listeners were preserved. Exact probe preview/rollback remains open under A29.

## Required continuation

The full owner objective remains active in [the repository audit worklist](docs/audit/REPOSITORY-AUDIT.md):

- Review every narrative/structured document and relevant source/test; inventory is not proof of review.
- Deliver missing shared SSH credential/key/password/recovery controls and per-service boot/Wake Lock policy.
- Complete remaining guest replay/rollback and GTK/cross-client terminal qualification while preserving the working guest.
- Reconcile every installed runtime component and reproduce the supported setup from a clean isolated target.
- Recheck P1–P3 acceptance scope, correct stale claims, and continue the remaining roadmap in order.

Graphics, inference, and NPU qualification remain separate; see [testing](docs/testing/README.md). License/provenance remain public-release gates.
