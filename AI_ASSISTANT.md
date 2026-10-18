# AI assistant instructions

## Project scope

Ternuxx is an independent project aiming to become a world-class mobile workstation in a pocket with CPU baseline and verified GPU/NPU acceleration. Treat native Termux and the existing Ternux Debian PRoot as complementary first-class layers: native tools and permitted Android-facing integrations have their place; the PRoot provides its Linux userland, established desktop/workloads, and configured GPU route. Hybrid workflows should join their strengths through scoped handoffs. The existing `soobujmiah/ternux` project and its Debian rootfs remain independent and must not be modified as part of Ternuxx work. The canonical checkout command is `./ternuxx`; `nativeternux` remains available as a compatibility entry point. Installed-path migration still needs a backward-compatible plan.

Read `README.md`, `CURRENT_STATE.md`, `PROJECT_MANIFEST.yaml`, `PROJECT_CLASSIFICATION.yaml`, `AI_ASSISTANT.md`, `SECURITY.md`, `docs/PRODUCT-VISION.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/KNOWLEDGE-SYNC.md`, `SKB_KNOWLEDGE_SYNC.md`, relevant ADRs, and task-relevant evidence in `docs/RESEARCH.md` before changing behavior. Keep vision-facing docs in my plain first-person voice. Do not turn my goals into generic marketing copy or claim that I verified something I have not. For existing Ternux PRoot GPU use, read `docs/PROOT-GPU.md` first.

## Owner context and evidence

When the canonical SKB checkout is available, verify its remote is `soobujmiah/skb`; read `ASSISTANT_CONTEXT.md` and `profile/assistant-guidance.md`, then only task-relevant linked material. Do not assume a local path or claim SKB alignment without checking it.

Repository source and live Git state determine implementation facts. Keep these evidence types separate:

- native Termux runtime;
- Debian PRoot runtime;
- Ternux source/documentation;
- owner-reported observations;
- untested design proposals.

A device node, driver library, Vulkan instance, or shader cache is not proof that an active GUI workload uses hardware acceleration. An NPU hardware specification or installed AI library is not proof that an intended process can access the NPU. For OpenGL, record the renderer from the same process environment and display as the workload; identify `llvmpipe` as software rendering. GPU, NPU, performance, and driver claims require physical-device/workload evidence and must include the observed package/runtime version and actual selected backend.

## Safety and ownership

- Keep work inside this repository unless the owner authorizes a specific additional path.
- Do not access shared/external storage or personal device data without explicit path-specific authorization.
- Do not install/remove/upgrade device packages, change Android/Termux settings, start/stop desktop processes, or drive device UI unless explicitly authorized for that operation.
- Do not rewrite `~/x.sh`, run Ternux cleanup, or modify/upgrade/remove/prune/minimize the existing Ternux Debian rootfs. Native/Hybrid work must preserve all demonstrated existing Ternux PRoot features; Ternuxx additions are opt-in and additive.
- Until an ownership-aware adapter exists, Ternuxx must not start or stop Ternux or claim its display/audio lifecycle. Existing Ternux GPU workloads are run from the Ternux Debian desktop.
- Keep package installation preview-first with explicit consent. Never describe a stub as implemented.

## Engineering workflow

- Inspect `git status`, current branch, and relevant diffs before editing; preserve unrelated changes.
- Make the smallest coherent change and update human-authored docs when behavior or evidence changes.
- Do not invent package availability, size estimates, supported devices, license terms, or runtime results. License is unresolved until an owner-approved license file exists.
- Run only checks appropriate to the change and report exactly what ran. Device checks require the authorization above.
- Do not commit or push unless the owner asks.
- Follow `docs/KNOWLEDGE-SYNC.md` for project documentation, deterministic status, and SKB knowledge return. Never give project CI an SKB write credential; SKB pulls registered project state. The phase documentation tool requires Python 3.9 or newer. Treat the generated phase blocks in `README.md`, `docs/ROADMAP.md`, and `docs/PHASE-STATUS.md` as read-only. After reviewing phase evidence, use `python3 tools/phase_docs.py complete ...`; use `refresh` to regenerate them. Never mark a gate complete from a commit or checklist alone.
- At handoff, summarize changed files, evidence, checks, known limits, and remaining work.


## Session handoff: SSH work and managed test shells

- The native Termux-side Codex integration is not ready. For repository implementation, connect to the available work shell with `ssh -p 8022 u0_a490@127.0.0.1`; use that shell to inspect and edit this Ternuxx checkout. Confirm the live runtime with `uname`, `$PREFIX`, and repository path instead of assuming which layer is active.
- Port `8023` is the loopback-only, Runit-managed SSH endpoint used for the managed repository test shell. When available, run `bash scripts/repo_test.sh` through `ssh -p 8023 u0_a490@127.0.0.1` and record that route distinctly from a direct 8022 run. Both endpoints currently use the same Ternuxx checkout.
- Do not store SSH passwords, keys, tokens, or private runtime state in repository documentation or evidence. Never expose 8023 beyond loopback without a separately reviewed remote-access plan.
- Authentication continuity: a future assistant does not inherit credentials from an earlier chat. The 2026-10-18 managed 8023 test used an owner-provided in-session SSH credential; no password or private key was persisted. Do not assume 8023 will authenticate in a later session. Use an owner-approved SSH agent/key provisioned outside the repository, or ask the owner to provide access through the approved secure channel. Changing `authorized_keys`, SSH authentication settings, or service configuration requires explicit owner authorization.
- Keep all implementation inside `soobujmiah/ternuxx`. The separate `soobujmiah/ternux` repository and its installed PRoot/rootfs are external dependencies to adapt through supported interfaces; do not edit that repository or mutate the existing guest/launcher as part of ordinary Ternuxx work.
- Current phase remains P3 (`in_progress`); consult `CURRENT_STATE.md`, `project/phase-state.json`, and the newest P3 gate audit before choosing the next task.
