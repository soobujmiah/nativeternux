# Serial roadmap audit — 2026-10-20

Phase: `P3`
Phase: `P4`
Phase: `P5`
Phase: `P6`
Phase: `P7`
Phase: `P8`
Phase: `P9`
Phase: `P10`

## Purpose and method

Reviewed the product vision, project manifest, phase state, roadmap gates, generated phase status, and the latest P3 management/boot and graphics/PRoot evidence. This is a plan audit only. It does not pass a phase gate, restart Termux, reboot the device, alter the existing Debian rootfs, or claim a capability that has not been verified.

The project should be considered complete against one explicitly supported target profile and the owner's selected Native, existing-PRoot, and Hybrid workflows. It should not require every Android device, Linux distro, optional app, Wine/Hangover workload, NPU, or a second PRoot profile to work. Unsupported optional capabilities must have a recorded feasibility result and be labelled unavailable or unverified. Public release additionally requires an owner-selected license and complete provenance.

## Serial phase review

| Phase | Audit result | Required outcome before advancing |
|---|---|---|
| P0 | Complete; project boundaries and evidence workflow exist. | No new gate identified. |
| P1 | Complete for the initial Android 16/aarch64/Termux target; other targets are uncertified. | Keep the target matrix narrow and date-sensitive package facts refreshed at release. |
| P2 | Complete for the current Native XFCE lifecycle. | Preserve the existing lifecycle guarantees; no new gate identified here. |
| P3 | Active, not complete. Owner visual review is accepted and the managed Cron script was manually exercised, but actual boot delivery is unqualified. General interactive PRoot TTY ownership (guest UID, cwd, attach/detach) is unqualified; installed boot/recovery helper copies differ from source; Android startup and concurrency/recovery acceptance remain open. | In order: define/fixture-verify interactive PRoot TTY ownership; close the supported-operation parity contract across CLI/TUI/Web/GTK; reconcile exact installed helper deployment with backup and tested rollback; finish recovery/concurrency and Android startup policy; then qualify cold boot only in a separately authorized window. If that window is not authorized, P3 remains active. |
| P4 | Implementation exists but the phase remains planned and unaccepted. Existing Debian must be preserved. Standalone :0 and shared-display :1 paths have evidence; the direct Debian GLX workload on :1 rendered with Zink/Turnip. Nested :2 only exposes a GLES context; DRI3 is unavailable and GLX draw is zero. Fresh-rootfs replay is fixture-tested only. | After P3, finish the adapter contract and reproduce setup on a separate disposable rootfs. Verify actual launch, display/audio, and selected existing Ternux workloads. Do not describe :2 as GPU-accelerated without a draw/presentation result. |
| P5 | Planned, with no exit evidence. The current device is the only qualified compatibility profile. | After P4, define the exact supported initial Android/Termux/ABI/distro/display/audio profile; all other pairings stay candidates until separately tested. |
| P6 | Planned; significant Native and direct Debian workload evidence exists, but ordinary workload API-aware routing, clean-install GPU provider reproduction, nested presentation, and NPU runtime/workload are open. | After P4/P5, complete workload-specific backend selection, API-safe fallback, named CPU fallback workloads, install reproduction, and comparable performance/thermal checks. Determine NPU feasibility; if inaccessible, record unavailable rather than blocking on unsupported hardware. |
| P7 | Planned; current app shortcuts are not a complete curated catalog/install lifecycle. | After P6, ship a small, supported catalog with official provenance, provider requirements, exact install/update/remove previews, and accurate CLI/Web guidance. Keep optional app breadth out of the base install. |
| P8 | Planned; no accepted end-to-end Native/PRoot/Hybrid boot-to-result evidence. | After P7, verify the selected boot profile, shared display/audio ownership, explicit file/argv handoff, result collection, and failure behavior in each mode. |
| P9 | No separate profile need is selected. The phase tool now supports a reviewed skip transition, but P9 has not been skipped and remains planned/optional. | After P8, run only for an owner-approved workload gap; otherwise, when P9 becomes active, create Gate: SKIP evidence and use the phase tool. Never target the current Debian rootfs. |
| P10 | Planned; public release is not ready. | Run final security/reproducibility/support review for selected capabilities, refresh docs/catalog/CI/device evidence, and resolve license/provenance before public distribution. |

## P3 remaining work in order

1. Define and fixture-verify general interactive PRoot TTY ownership: guest UID, working directory, process identity, environment, output, and attach/detach behavior. Do not start guest lifecycle implementation before P4.
2. Use the current capability matrix to map each supported operation across CLI, TUI, Web, and GTK. Agree the supported action set, authorization/confirmation behavior, and any technically necessary owner-accepted exception.
3. Reconcile the installed boot/recovery helper files against source using an exact preview, preserved backup/state, explicit apply, and tested rollback.
4. Close recovery, operation-lock/concurrency, and Android startup/background policy checks.
5. Qualify Termux:Boot cold-start delivery only in a separately authorized device-boot window. The current session-preservation instruction takes priority; without that window, record the gate as blocked and keep P3 active.
6. Review the P3 exit gate; only then activate P4.

## Serial ordering and definition of completion

The critical path is P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → P10. P9 is an optional branch from P8 and must be explicitly skipped with evidence when no approved gap exists. Only one phase is active at a time; future-phase notes are preparation only and do not authorize implementation or phase completion.

Project completion means the supported target can reproduce the selected Native, existing Debian PRoot, and Hybrid workflows from Ternuxx-managed configuration without replacing the current rootfs; shared management clients accurately expose the supported operations; graphics claims are tied to actual named workloads and include API-compatible CPU fallback; unsupported capabilities are clearly reported; tests, CI, recovery, documentation, and rollback evidence pass. NPU hardware access is not a mandatory claim: its feasibility must be assessed, and unavailable/unverified is an acceptable honest result. P9, unselected distros, broad device certification, and optional Wine/Hangover apps are not blockers unless selected into release scope.

## Evidence

- Current state and active order: `project/phase-state.json`, `docs/ROADMAP.md`, and generated `docs/PHASE-STATUS.md`.
- P3 gaps and owner review: `docs/evidence/2026-10-20-p3-owner-visual-and-boot-cron-recheck.md`, `docs/evidence/2026-10-20-management-client-parity-audit.md`, and `docs/architecture/CAPABILITY-MATRIX.md`.
- P4/P6 graphics boundary: `docs/evidence/2026-10-20-graphics-live-recheck.md` and `docs/evidence/2026-10-20-proot-full-gui.md`.
- Product target and scope: `docs/PRODUCT-VISION.md` and `PROJECT_MANIFEST.yaml`.

## Acceptance criteria

- Phase order, prerequisite gates, optional-phase behavior, and project completion are explicit and machine-rendered status agrees with the authored roadmap.
- Existing work is labelled preparation/partial until its phase exit gate is accepted.
- The current supported target and the remaining P3 serial action are unambiguous.
- No active phase is completed by this audit.

## Gate status

Review only; P3 remains active and P4–P10 remain planned.
