# Roadmap

Ternuxx is a Native Termux-only Android workstation manager. The owner selected this scope on 2026-10-24 and authorized retirement of PRoot support, including installed guests and manager packages. The previous multi-provider roadmap is preserved as [historical planning](history/ROADMAP-pre-native-only-2026-10-24.md); it is not the active product plan.

<!-- generated:phase-table:start -->
| ID | Phase | Status | Completed / skipped |
|---|---|---|---|
| P0 | Repository foundation and evidence baseline | completed | 2026-10-17 |
| P1 | Requirements and CPU/GPU/NPU compatibility research | completed | 2026-10-17 |
| P2 | Safe native desktop lifecycle | completed | 2026-10-18 |
| P3 | Doctor, management, and recovery | completed | 2026-10-21 |
| P4 | Owner-directed retirement of former PRoot provider | completed | 2026-10-23 |
| P5 | Native Termux profile compatibility | completed | 2026-10-23 |
| P6 | CPU/GPU/NPU capability, optimization, and fallback | completed | 2026-10-24 |
| P7 | Native apps and curated software catalog | completed | 2026-10-24 |
| P8 | Native workload and accelerator routing | completed | 2026-10-24 |
| P9 | Optional isolated workload profile | skipped | skipped 2026-10-24 |
| P10 | Hardening, release, and support | completed | 2026-10-24 |
<!-- generated:phase-table:end -->

## Active work

<!-- generated:active-work:start -->
All required phases are resolved; see evidence for completed gates and skipped optional phases.
<!-- generated:active-work:end -->

## Current work

1. Keep the retired PRoot guest, terminal, graphics-provider, and app-menu routes absent from the source and clients.
2. Keep CLI, TUI, Web, and GTK behavior aligned with the Native operations actually exposed by the shared service.
3. Keep current documentation and schemas Native-only; retain dated evidence clearly labeled as historical.
4. Run the complete Native Termux test suite and reconcile phase/evidence records with the results.
5. Continue device-specific qualification for graphics, audio, boot delivery, SSH, backup, and recovery without claiming support beyond observed evidence.

## Completion criteria

- No supported command, UI action, package plan, or schema provisions or routes to a PRoot guest.
- Native Termux remains usable with no guest tools or guest containers installed.
- Every client exposes only implemented Native operations, with the same authorization and preview/confirmation rules.
- Current docs describe Native Termux; historical guest records are dated and indexed as history.
- The full test harness, document/link audit, and Native live checks pass, with limitations recorded.

Public release additionally requires a selected license, provenance review, and owner acceptance of the release artifact.
