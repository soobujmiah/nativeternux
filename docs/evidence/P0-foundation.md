# P0 foundation completion evidence

- Phase: `P0`
- Date: `2026-10-17`
- Commit: `2a06523a40acbaa451f97a44630646ef6ef0d430` (worktree contains the reviewed, uncommitted project changes)
- Device/runtime: Termux on the owner's Android device, inspected over SSH using read-only commands; repository documentation and generated files edited only inside `~/nativeternux`.
- Gate: PASS

## Acceptance criteria

- [x] Owner-approved scope and boundaries are reflected in the project docs: Native Termux and existing Ternux Debian PRoot are complementary first-class layers; Hybrid mode connects them through explicit handoffs; the original Ternux project/rootfs remains independently owned.
- [x] `AI_ASSISTANT.md`, architecture, installation status, research, README, and roadmap distinguish implemented scaffold behavior from future work, and distinguish native Termux GPU evidence from the separately configured PRoot route.
- [x] `python3 tools/phase_docs.py refresh` regenerated README, roadmap phase status, and `docs/PHASE-STATUS.md` from `project/phase-state.json`.
- [x] Completion is recorded only through the phase tool and requires a repository-local evidence document with the phase ID, passing gate, acceptance criteria, and evidence sections.
- [x] Changes are confined to NativeTernux documentation/scaffold files. No original Ternux files, device packages, Android settings, rootfs contents, or desktop processes were changed.

## Evidence

- Owner direction in the conversation: build a CPU/GPU/NPU-capable pocket workstation; make native Termux and existing Ternux PRoot complementary; retain the existing PRoot setup and capabilities; document before feature implementation; keep device actions read-only unless separately authorized.
- Reviewed `README.md`, `bn/README.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/INSTALLATION.md`, `docs/RESEARCH.md`, `docs/PROOT-GPU.md`, and `AI_ASSISTANT.md` against the current CLI/source and phase state.
- Generated phase docs with `python3 tools/phase_docs.py refresh`.
- `git diff --check` completed without errors.
- Read-only Termux inspection confirmed the existing CLI phase state and local repository sources; no package transaction or desktop lifecycle command was run.

## Known limitations

- P0 establishes the documented scope and evidence workflow; it does not implement native desktop lifecycle or a Ternux PRoot adapter.
- At the P0 completion point, P1 research was still pending. It subsequently passed as recorded in [P1 compatibility evidence](P1-compatibility-research.md); later additions are dated separately.
- Live PRoot renderer status was not re-tested in this review; prior documentation remains source-verified, not a new runtime result.
