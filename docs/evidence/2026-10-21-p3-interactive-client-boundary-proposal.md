# Withdrawn P3 interactive-session client boundary proposal — 2026-10-21

Status: withdrawn by the owner's updated requirement. Do not treat the CLI/TUI-only boundary below as an accepted exception or P3 gate evidence.

The owner requires interactive terminal support in CLI, TUI, Web, and GTK, while prohibiting an unrestricted Web/GTK shell and Android security-boundary changes. The earlier CLI/TUI-only proposal is superseded by [the shared interactive PRoot terminal design](../architecture/INTERACTIVE-PROOT-TERMINALS.md), which audits the current components and defines a phased broker/client plan.

P3 remains active. No owner exception is recorded, no cross-client PTY broker exists, and no Web/GTK interactive terminal is implemented. The updated P3 review is [here](2026-10-21-p3-gate-review-followup.md).

## Evidence

- Owner requirement recorded 2026-10-21 in the active task.
- Current architecture and phase boundary: `docs/architecture/INTERACTIVE-PROOT-TERMINALS.md` and `docs/ROADMAP.md`.
