# Current state

- **Repository:** `soobujmiah/nativeternux` (owner-reported private; current remote verified)
- **Project type:** `cli-tool` with automation capability; see `PROJECT_CLASSIFICATION.yaml`.
- **Current phase:** P2 — Safe native desktop lifecycle. Generated milestone details are in [Phase status](docs/PHASE-STATUS.md).
- **Implementation authority:** source in this repository. Product and technical evidence are documented under `docs/`.
- **Mechanical Git/CI status:** `.repo/STATUS.md` is initialized locally with generated Git state and build/test `unknown`. Workflows are present but not pushed or run, so this is not CI evidence. Once onboarding is complete, `.repo/STATUS.md` remains the generated authority; do not copy its commit/build/test values here.

## Implemented and verified

- A CLI/documentation scaffold, phase status generator, and initial source for ownership-aware native desktop lifecycle exist.
- P0 foundation and P1 compatibility research are recorded complete with evidence files.
- Official Termux X11 desktop package candidates and Hangover 11.16 candidates were inspected read-only in configured package indexes.
- Native Vulkan returned `VK_ERROR_INCOMPATIBLE_DRIVER` for the recorded Adreno 825 configuration; native DXVK is not qualified.

## Planned or not yet verified

- The `install --yes` APT transaction exists in source but has not been run or qualified on device. Native desktop lifecycle source has not been executed, runtime-tested, or device-qualified; P2 remains in progress.
- Existing Ternux PRoot adapter and live guest renderer have not been validated by NativeTernux.
- Wine/Hangover is an optional candidate runtime; no Windows app or native graphics backend is qualified.
- No Termux-accessible NPU runtime/bridge is established.
- SKB status runtime, schema, bridge, and workflow source are installed locally; GitHub Actions has not run and SKB registry registration remains pending onboarding gates.

## Safety boundaries

No package installation, Android setting change, desktop/service start/stop, Ternux launcher/rootfs modification, or shared-storage scan is authorized by this status record. The current owner instruction keeps device operations read-only. Follow `AI_ASSISTANT.md` and the task-specific owner instruction. The project must preserve the separate Ternux installation and its demonstrated capabilities.

## Current handoff

Documentation and implementation work is ongoing. The detailed phase gate, evidence, limitations, and next work are in [the roadmap](docs/ROADMAP.md), [research](docs/RESEARCH.md), and [knowledge synchronization contract](docs/KNOWLEDGE-SYNC.md). This update inspected and revised source and documentation only; no test suite or device mutation was performed.
