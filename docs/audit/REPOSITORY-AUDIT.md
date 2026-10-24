# Current repository audit

**Reviewed:** 2026-10-24
**Branch/base:** `main` at `33a465c` with an uncommitted Native-only migration worktree.
**Runtime:** Native Termux on Android 16/API 36, ABI `arm64-v8a`, Termux `0.119.0-beta.3`.
**Scope:** product/runtime alignment, current source routes, shared clients, package/catalog contracts, tests, current documentation, and dated evidence. The former long-form multi-provider audit is retained as [historical work](../history/REPOSITORY-AUDIT-pre-native-only-2026-10-24.md).

## Verified current state

- **Product boundary:** Native Termux-only is the accepted owner direction. Six PRoot-Distro guests and both manager packages were removed. Active guest source modules, routes, schemas, terminal broker, VirGL path, GTK guest controls, and feature-specific tests/tools were retired. Old implementation/evidence documents are historical, not supported instructions.
- **Native runtime:** a read-only post-qualification recheck reports display `:1`, live Ternuxx supervisor/X11/XFCE, and `ternuxx-native` audio owner. The Termux app and Native services remained open during the audit. Shared/external storage was not accessed. The same check found `proot` and `proot-distro` packages and executables absent and the PRoot-Distro containers directory empty; see the [runtime recheck record](../evidence/data/2026-10-24-native-runtime-post-qualification.json).
- **Current device profile:** Android 16/API 36, model `25053RT47C`, Android ABI `arm64-v8a` / Termux package architecture `aarch64`, Termux `0.119.0-beta.3`. Exact package, display, and audio details are in the [profile report](../testing/reports/2026-10-24-native-profile-25053RT47C.md).
- **Graphics:** bounded Native OpenGL and GLES draws on Adreno 825 pass through the current experimental candidate; forced llvmpipe and a failed-Zink-to-llvmpipe fallback also pass. Vulkan enumeration and a bounded on-screen `vkcube` draw now pass after correcting inherited loader-path precedence. See the [direct P6 recheck](../evidence/2026-10-24-native-graphics-fallback-recheck.md); do not claim general application or inference acceleration.
- **Shared client contract:** CLI/TUI use the local management service, Web calls the authenticated loopback adapter, and GTK calls the narrow local bridge. Current operation allowlists and status differences are maintained in the [client capability matrix](../architecture/CAPABILITY-MATRIX.md); tests cover the shared authorization and request contract. Visual/client parity remains incomplete.
- **Guidance:** `tx help` and `tx guides` provide Native commands and an interactive setup path. `tx install preview` is the base-profile package planner; it is not an arbitrary optional app-store lifecycle.
- **Test evidence:** the full harness passed 690 tests in 110.249 seconds on 2026-10-24. This is repository fixture evidence; device-only claims remain tied to their direct Native evidence. The focused Doctor module and graphics candidate verification are recorded separately.
- **Document audit:** the current indexed scope has zero broken local Markdown links. The generated inventory covers current docs and structured records; many historical records were indexed, not read individually. It is not represented as a full content review.

## Remaining project gates

| Phase | Status | Open gate |
|---|---|---|
| P6 — Native compute and fallback | Completed as a capability assessment | The named bounded CPU path and rendering fallback are recorded; stock and experimental graphics are separated; offline remains unverified, GPU inference/NPU remain unavailable, and the experimental candidate is outside release support. Longer stability and reproducible distribution remain release limits. See the [P6 completion review](../evidence/2026-10-24-p6-completion-review.md). |
| P7 — Native apps/catalog | Active | Scope audit selected `htop`, `tmux`, and `tree` from official `termux-main`; a read-only simulation resolved the three packages plus `utf8proc`, with no upgrades/removals. Implement typed install/update/remove previews, exact confirmation, results, and aligned CLI/TUI/Web/GTK controls. See the [P7 scope audit](../evidence/2026-10-24-p7-native-catalog-scope.md). |
| P8 — Native end-to-end workflows | Planned | Verify selected Native boot-to-workload-to-result paths, file handoff, display/audio ownership, logs, failure handling, and recovery without stopping the active desktop. |
| P9 — optional isolated profile | Deferred | No isolated guest provider is in the selected product. Skip only through the phase workflow with evidence when P9 becomes active. |
| P10 — hardening and release | Planned | Re-run security, recovery, clean-install, documentation, CI, and provenance checks. No repository license exists; public redistribution/release remains blocked pending owner/legal decision. |

## Current safety and device risks

- The latest read-only Doctor report warns that the Native SSH configuration has wildcard bind scope and password authentication enabled; process-to-port correlation and external reachability are unknown. It has not been changed in this work. Review `tx ssh status --json` and the documented managed/development SSH boundary before exposing remote access.
- The graphics candidate is experimental and has no reproduced clean-install distribution path. Doctor reports the stock host path separately from candidate verification. The installed `llama-cpp` package and pinned model support the new bounded CPU inference workflow. The package lifecycle remains Termux-owned; see the [workflow evidence](../evidence/2026-10-24-native-cpu-inference-workflow.md).
- Doctor reports Termux:Boot package/receiver state but system delivery policy remains unknown. No reboot or app restart was attempted.
- The owner-reported backup was not inspected. This audit did not open or verify it.

## Audit procedure and current authority

1. Treat repository source/tests and current live Git/runtime state as implementation authority; use SKB for owner context and dated research only for its observation window.
2. Use [phase state](../../project/phase-state.json) for gate order, [feature matrix](../testing/FEATURE-MATRIX.yaml) for current capability summaries, [client matrix](../architecture/CAPABILITY-MATRIX.md) for interface reach, and [device profile](../testing/DEVICE-COMPATIBILITY.md) for hardware claims.
3. Use the [documentation inventory](document-inventory.json) for path/hash coverage and link findings. An indexed or hashed document is not a reviewed claim.
4. Preserve prior dirty Web reload/reconnect changes and their evidence; do not reset or overwrite existing work.
5. Keep the Termux app, active desktop, SSH, and other Native services open. Do not traverse shared/external storage.

The earlier multi-provider findings and exact dated claims are preserved in [the archived audit](../history/REPOSITORY-AUDIT-pre-native-only-2026-10-24.md). Do not use that snapshot as current runtime guidance.
