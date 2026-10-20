# AI assistant instructions

## Project scope

Ternuxx is an independent project aiming to become a world-class mobile workstation in a pocket with CPU baseline and verified GPU/NPU acceleration. Treat native Termux and the existing Ternux Debian PRoot as complementary first-class layers: native tools and permitted Android-facing integrations have their place; the PRoot provides its Linux userland, established desktop/workloads, and configured GPU route. Hybrid workflows should join their strengths through scoped handoffs. The `soobujmiah/ternux` source project remains independent. Its existing Debian rootfs is the owner-selected Ternuxx adapter target and may be changed only through the bounded Ternuxx guest plan described below. The supported source-checkout command is `./tx`; the installed `tx` shim dispatches to `$HOME/ternuxx`. Installed paths use the Ternuxx state and library directories.

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
- Do not rewrite `~/x.sh`, run broad Ternux cleanup, or replace/reset/prune/minimize the existing Debian rootfs. The owner has directed Ternuxx to become its setup and management layer: guest changes are allowed only through a Ternuxx-owned, exact-target preview with explicit apply, preserved user data, and a tested rollback. Preserve `db`, `droot`, `x.sh`, `xgo`, and `killx` behavior.
- Do not call the legacy Ternux CLI from new code. Retire its exact host/guest command files only after Ternuxx replacement and workload verification, with a reviewable preview and backup/rollback. Never use `ternux uninstall`.
- Until an ownership-aware adapter exists, Ternuxx must not start or stop Ternux or claim its display/audio lifecycle. Existing Ternux GPU workloads are run from the Ternux Debian desktop.
- Keep Native and Debian package installation preview-first with explicit consent. Debian Bionic/Termux libraries must never cross into the Debian glibc guest. Never describe a stub as implemented or a manifest as a working installer.

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
- Port `8022` is the owner-started native Termux repository development shell. Use it for repo inspection, implementation, and repository test runs. Port `8023` is the loopback-only, Runit-managed Ternuxx SSH/CLI endpoint and is part of the product being developed; use it to exercise managed CLI/service behavior, not as the default repo-work shell. Both endpoints currently reach the same Ternuxx checkout, but their roles must be recorded distinctly.
- Do not store SSH passwords, keys, tokens, or private runtime state in repository documentation or evidence. Never expose 8023 beyond loopback without a separately reviewed remote-access plan.
- Authentication continuity: use credentials provisioned outside the repository. Do not assume either endpoint will authenticate in a later session. Never persist passwords or private keys in repo files/evidence. Changing `authorized_keys`, SSH authentication settings, or service configuration requires explicit owner authorization.
- Keep all implementation inside `soobujmiah/ternuxx`. The separate `soobujmiah/ternux` repository and its installed PRoot/rootfs are external dependencies to adapt through supported interfaces; do not edit that repository or mutate the existing guest/launcher as part of ordinary Ternuxx work.
- Current phase remains P3 (`in_progress`); consult `CURRENT_STATE.md`, `project/phase-state.json`, and the newest P3 gate audit before choosing the next task.

## Latest continuation: 8023 reconciliation (2026-10-18)

- P0 stays complete. Source implementation commit: `ec9a6aff58f7ecd945700998da534d17e9c0ee52`; documentation continuation: `75582514640c`; deterministic test-state commits follow these source commits.
- The installed 8023 Runit run file was a stale deployment: it matched historical same-path blob `025023e`, while current source differed in four state/log/chmod lines. Preview-first reconciliation was applied as operation `fffd3f74f9ce416f8b094a2cde019ce1`. Installed and source SHA-256 now match `1dc73681a09d606b265db8add60e4870c144a50b31da7b3ba0a7db3c7ab932f6`; managed sshd config was unchanged.
- The 8023 service remained `run` under PID 13061; a loopback SSH banner responded after deploy. No Runit up/down/restart, 8022 modification, SSH exposure/auth change, or reboot occurred. A private rollback snapshot remains available; its preview shows the reverse diff. Device rollback was not applied.
- Port 8022 remains the owner-started manual development channel and was left connected. Do not merge its purpose/config with 8023.
- Full Native Termux suite: 308/308 via `bash scripts/repo_test.sh`. Repository knowledge verification: 0 findings. Test status is local evidence, not CI/build qualification.
- Listener socket-to-PID ownership remains `UNVERIFIED`: `/proc/net/tcp` and `/proc/net/tcp6` are permission denied. Reboot readiness remains `UNVERIFIED`; no reboot. 8023 effective config remains loopback with password, key, and keyboard-interactive authentication enabled; 8022 config remains separately wildcard/password configured with reachability unknown. No auth or exposure policy was changed.
- Existing Debian PRoot rootfs/packages/workspace and `db`/`droot`, `x`/`x.sh`, `xgo`, `killx` were inspected read-only and left intact. PRoot-to-native SSH auth was unavailable, so tests ran through 8022 in Native Termux.
- Evidence and procedures: `docs/evidence/2026-10-18-8023-reconciliation.md`, `docs/testing/8023-deployment-and-lifecycle.md`, `docs/architecture/SSH-LIFECYCLE.md`.
- Next P3 action: establish listener ownership using a permitted source, then run the separate 8023 lifecycle qualification plan while preserving 8022. Reboot remains blocked on explicit owner approval. After P3 ownership gates, continue P4 existing-Debian adapter work without replacing or mutating the workstation.

## Master direction and current preservation baseline (2026-10-18)

- Follow the owner-approved direction: preserve and adapt the existing Debian PRoot; Native Termux is the host control plane. CLI, interactive Terminal/TUI, Web UI, and Graphical UI must share one service and operation contract. See PRODUCT-VISION.md, ARCHITECTURE.md, architecture/UNIFIED-WORKSTATION.md, and the established P0-P10 roadmap.
- Read-only baseline at commit 5232a20b63c5f9f66d8f3e74208ed5bff8c4340a: Debian 13.7, guest user sbj, existing rootfs at $PREFIX/var/lib/proot-distro/containers/debian/rootfs; pre-existing PID 16526 was left untouched. Full evidence: docs/evidence/2026-10-18-existing-workstation-baseline.md.
- Ternux GitHub main was pinned at 9fda63162426f77ee575b5f6729d8799a30f51b7. Its docs cover Zink/Turnip, optional CPU/Vulkan llama.cpp, and experimental SM8735 HTP. Live host reports Zink/Vulkan with renderer unknown; installed v1.4.0 lacks the documented extension command. Optional extension source does not prove installation.
- Owner clarified that Native aliases and ~/x.sh are intentionally customized for the active GUI workflow. Do not label that as stale drift or restore upstream defaults. Never rewrite x.sh, x, xgo, or killx. Ternuxx supports the explicit selected-app handoff described below without taking over session lifecycle.
- db, droot, x, xgo, and killx semantics were inspected; existing PRoot and GUI workflows remain intact. P3 is active, P4 is planned. 8023 listener PID ownership and reboot readiness remain UNVERIFIED; 8022 remains the separate owner-started development channel.

## Latest continuation — Native Ternux X11 app handoff (2026-10-18)

- Work remains in Native Termux under $HOME/ternuxx, reached through owner-started 8022; soobujmiah/ternux is reference/runtime only.
- Added optional proot.app.launch args session_owner=ternux and explicit display; CLI: ./ternuxx management app launch files --session ternux --display :1. Native Ternux status/backend and guest X11 reachability are checked read-only; no Ternux lifecycle or Android activity is invoked. Existing Ternuxx default is preserved.
- Live Debian :1 glxinfo -B reports Mesa 25.0.7, Zink/Vulkan 1.4, Adreno 825 MESA_TURNIP, Accelerated yes. Native Ternux status itself reports renderer unknown. Thunar PID 17894 started on the existing session and remains owner-closeable; GUI visibility is not independently observed.
- Focused tests 12/12; final full Native Termux suite 312/312; repo knowledge verification 0 findings. Evidence: docs/evidence/2026-10-18-ternux-session-app-handoff.md. P3 stays active and P4 planned; no reboot, session lifecycle action, x.sh/killx edit, or rootfs/package change.
- Next: after the owner closes the Thunar test window, continue P4 with session selection and shortcut routing through shared interfaces, then bounded existing-Debian inventory. Keep P3 SSH listener ownership/lifecycle as a distinct gate.

## 2026-10-18 live continuation: state path mismatch

At HEAD 5232a20b63c5f9f66d8f3e74208ed5bff8c4340a, default CLI status initially missed an active :1 desktop because the supervisor used a different recorded state directory. Added strict same-checkout state discovery with private HOME path and PID/start-time/command-marker/child validation; status/start/stop use it and ambiguous candidates fail closed. Native status now reports running; desktop lifecycle fixtures passed 12/12 and full suite 313/313. No live process was signaled. Thunar's prior PID is absent; visibility remains unknown. netstat TCP enumeration is unsupported and lsof exposed no listener rows, so 8022/8023 ownership stays UNVERIFIED. Evidence: docs/evidence/2026-10-18-live-session-state-reconciliation.json.


## Latest verified continuation — state discovery, Doctor, and SSH binds (2026-10-18)

- Base HEAD: `5232a20b63c5f9f66d8f3e74208ed5bff8c4340a`; native checkout `$HOME/ternuxx`; edits remain uncommitted. Continue implementation only through owner-started SSH 8022.
- The desktop state discovery helper now reconciles CLI and read-only Doctor. Native status and Doctor verify the existing :1 supervisor, Termux:X11, and XFCE session. The full Native Termux suite passed 315/315 after the Doctor discovery regression test.
- ADB read-only observation confirms actual 8022 wildcard listeners and 8023 loopback listener. Exact ownership is VERIFIED by matching ADB `/proc/net/tcp*` inodes against same-UID Native Termux FDs: 8022 PID 16337 FDs 6/7 map to IPv6/IPv4 wildcard sockets; 8023 PID 13449 FD 6 maps to `127.0.0.1:8023`, under Runit PID 13061. Keep the 8022 wildcard exposure visible; do not change SSH policy without owner approval.
- Existing Debian PRoot process 16526 and native GUI :1 remain present. A scoped ADB screenshot visibly confirmed the floating XFCE desktop; the temporary capture was deleted after inspection. No reboot, live GUI/service lifecycle action, PRoot mutation, rollback, commit, or push occurred. Reboot readiness remains UNVERIFIED; 8022 external reachability was not tested.
- Next: perform the separate 8023 lifecycle qualification without disrupting 8022 and without reboot. Reboot readiness requires explicit owner approval; 8022 external reachability is outside the checks performed so far. Details: `CURRENT_STATE.md` and `docs/evidence/2026-10-18-live-session-state-reconciliation.json`.


## Latest verified continuation - 8023 lifecycle and shared state (2026-10-18)

Base HEAD `5232a20b63c5f9f66d8f3e74208ed5bff8c4340a`; Native Termux checkout `$HOME/ternuxx`; changes remain uncommitted. The installed `$PREFIX/bin/ternuxx` shim now invokes the checkout through `$PREFIX/bin/bash`; legacy `$PREFIX/bin/nativeternux` and its library remain preserved. The 8023 run definition is deployed from source; stale lease PID 12951 was removed only after the kernel confirmed it absent. Current Runit service and loopback SSH banner pass; checkout and installed CLI share one active native.sshd lease. A key-only BatchMode attempt was denied, then owner-provided interactive authentication returned `authenticated-loopback-ok`. ADB socket inode 2372520 maps to managed sshd PID 22443 FD 6 and Runit ancestry; current authenticated readiness/listener ownership are VERIFIED. 8022 inode 135149 maps to PID 16337 FD 7 and remained active. Full Native Termux suite passed 324/324; focused entrypoint/service/wakelock tests passed 18/18. No reboot, commit, or push. Reboot remains UNVERIFIED. Evidence: `docs/evidence/2026-10-18-cli-entrypoint-state-reconciliation.md`.


## Current P3 continuation — 2026-10-19

Native implementation is in `$HOME/ternuxx`, accessed through owner-started SSH 8022. Base HEAD is `5232a20b63c5f9f66d8f3e74208ed5bff8c4340a`; working tree includes existing uncommitted edits. Read-only PRoot inventory now adds host process candidates from `/proc`; PIDs are candidates only and do not prove distro/session ownership. Never enter Debian or control/stop a PRoot process as part of this status operation. Focused diagnostics and management tests passed 46/46; live `proot status --json` returned PID 16526 as an unverified host process candidate, and the full Native Termux suite passed 326/326. Continue with phase/docs synchronization and final diff review before selecting next P3 acceptance. Preserve 8022, managed 8023, Debian rootfs, native GUI `:1`, and launcher workflows. Reboot remains unverified and prohibited without explicit approval. Evidence: `docs/evidence/2026-10-19-proot-process-inventory.md`.
