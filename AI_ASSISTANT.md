<!-- deterministic-state-bridge: ternuxx -->

**Machine-generated operational state:** see [`.repo/STATUS.md`](.repo/STATUS.md). Cross-project SKB registry state is in [the SKB repository registry](https://github.com/soobujmiah/skb/tree/main/projects/registry).

# Ternuxx Codex instructions

## Product scope

Ternuxx is a Native Termux-only Android workstation manager. The owner directed removal of all PRoot support, including the live Debian and replay guests, on 2026-10-24 and confirmed an existing backup. Native boot/recovery, SSH, CLI, management, state, desktop, graphics/audio reporting, and native workloads remain the product. Do not reintroduce PRoot, Debian guest management, hybrid routing, or PRoot package dependencies unless the owner changes this direction.

Keep interactive help and the existing CLI/TUI/Web/GTK paths easy to use for supported Native functions. `tx` is the public command. Use only `TERNUXX_STATE_DIR`, `$HOME/.local/share/ternuxx`, and `$PREFIX/lib/ternuxx` for product state/runtime modules. License remains unresolved unless an owner-approved LICENSE file exists.

## Required context

For non-trivial work, verify the canonical SKB checkout remote is `soobujmiah/skb`; read `ASSISTANT_CONTEXT.md`, `profile/assistant-guidance.md`, and only task-relevant linked material. Use SKB `standards/policy-resolution.md` for consequential authorization decisions. Dated claims are snapshots; check live project state when currency matters.

Read `README.md`, `CURRENT_STATE.md`, project manifests/classification, `SECURITY.md`, product vision, roadmap, architecture, knowledge-sync docs, relevant ADRs, and task-related research/evidence before changing behavior. Source, tests, and live Git/runtime state govern implementation facts. Preserve evidence classes: Native Termux runtime, historical PRoot/debian runtime, separate Ternux source/documentation, owner report, and untested proposal.

## Runtime and execution

This checkout runs in Native Termux on Android, not PRoot. Confirm with `uname`, `$PREFIX`, `$HOME`, and repository path. Work in `/data/data/com.termux/files/home/ternuxx` through the configured Native development shell (`ssh termux`, port 8022) when available; if it is unavailable, use the verified Native checkout directly and record that limitation. Never use the product's 8023 endpoint as the default repository-work shell.

Do not close the Termux app. Do not stop the Native desktop, SSH, Runit, or other owner-managed services unless the user explicitly asks for that exact operation. Do not access `/sdcard`, `/storage/emulated/0`, or unrelated personal/shared storage. Do not modify Android settings or install/remove/upgrade device packages unless the user explicitly authorizes that operation.

The owner explicitly authorized the current full PRoot removal, including all installed distro containers and the `proot`/`proot-distro` packages. Apply only to the verified PRoot-owned targets, use exact named operations, and verify inventory afterward. Do not traverse or alter shared/external-storage targets. The backup is owner-reported and was not independently checked.

## Engineering and evidence

- Inspect Git status, branch, and diffs before editing; preserve pre-existing dirty work and history.
- Keep changes task-scoped and update human-authored documentation/evidence when behavior changes.
- Native package changes are preview-first. Never claim a manifest is an installer, or a stub is implemented.
- Run relevant tests and exact live Native checks. Report only commands/results actually observed; keep device evidence separate from fixture/CI evidence.
- Do not infer GPU/NPU workload acceleration from device nodes, driver files, or context creation. State actual backend, workload, version, and target evidence.
- Follow `docs/KNOWLEDGE-SYNC.md` for project state; use `tools/phase_docs.py` for phase transitions and `tools/repo_knowledge` for generated `.repo` state. Never hand-edit generated `.repo` files or commit credentials/private runtime state.
- Standing owner authorization (2026-10-22): commit and push completed, reviewed work to the configured project branch; no force-push, history rewrite, broad cleanup, unrelated writes, or unapproved destructive operation.

At handoff, list changed files, evidence, checks, limits, and remaining work.
