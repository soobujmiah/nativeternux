# Master initiative Phase 0 — repository and environment audit

**Audit snapshot:** 2026-10-17 13:50 UTC
**Launch follow-up:** 2026-10-17 14:10 UTC; read-only Termux SSH session.
**Ternuxx repository:** `soobujmiah/ternuxx`, `main`, HEAD `1a891faabc925136c1801f40194b0969d28041df`
**Status:** evidence collected; owner review remains the Phase 0 exit gate.
**Scope:** read-only inspection of the Ternuxx repository, live GitHub metadata/Actions, current Termux/Android facts accessible from this PRoot shell, and the independent Ternux repository's public `main` source/docs. No implementation or device mutation was performed.

This report applies the owner's new Master Project Execution phases (0–9). It does not rewrite or advance the repository's existing generated P0–P10 phase state. The earlier [repository readiness audit](../readiness/REPOSITORY-AUDIT.md), [feature matrix](../testing/FEATURE-MATRIX.yaml), [testing overview](../testing/README.md), and [unified architecture proposal](../architecture/UNIFIED-WORKSTATION.md) remain supporting records.

## Executive assessment

Ternuxx is currently a **Bash Termux desktop lifecycle project**, not yet the unified workstation described by the master prompt. It has a package-preview/install path and initial native X11/XFCE start/stop/status implementation, but no product tests or device qualification. CLI help still describes those mutating commands as stubs, which is a material safety/documentation defect.

The live device exposes the Adreno 825 KGSL node, has Termux:X11, Termux:Boot, Termux:API, and Shizuku APKs installed, and has the Termux API command package. The native XFCE packages are not installed. Installed companion apps do not prove that Shizuku is running/authorized, Android capabilities are granted, boot scripts are configured, or a desktop can launch.

The most important reuse finding is that the independent `soobujmiah/ternux` project already documents **CPU/Vulkan llama.cpp** tests and experimental **Hexagon HTP** and **QNN** routes in its current `main`. These are external Ternux/PRoot assets, not Ternuxx features. The HTP record includes real correctness failures and incomplete operator coverage; the QNN image route lacks independent stage-tensor correctness. Ternuxx should investigate a narrow adapter to those existing services/extensions before building a second inference runtime. Preserve that repository, its launcher, rootfs, workloads, and lifecycle.

**Recommended next gate:** owner review of this baseline and the shared-backend/API/security/Launch Manager proposals; then approve a bounded Phase 1 decision set. Do not start a dashboard, GTK/Qt application, AI runtime, boot automation, or PRoot lifecycle control before the corresponding contracts and acceptance tests are approved.

## 1. Repository baseline

| Item | Status | Verified evidence | Interpretation |
|---|---|---|---|
| Live repository | `VERIFIED` | `gh repo view`: `soobujmiah/ternuxx`, `PUBLIC`, default `main`; origin matches | Public source visibility is not an open-source license. |
| Intended product name | `OWNER_DECIDED` | Owner has fixed Ternuxx | Product branding is approved; repo slug, CLI, package IDs and much active text still say Ternuxx. |
| Intended `soobujmiah/ternuxx` slug | `UNKNOWN` | Authenticated `gh repo view` could not resolve a repository at that name on audit date | This does not prove slug availability or reserve it. No rename/repository setting was changed. |
| Local source snapshot | `VERIFIED` | `main`, HEAD equals `origin/main`, short history is five commits | The worktree already contains uncommitted documentation changes from earlier authorized work; those were preserved. No source-file edits were present. |
| Branches | `VERIFIED` | Local clone has only `main` and `origin/main` | No feature branch is available in this checkout. |
| Source languages | `VERIFIED` | Tracked implementation inventory: Bash and Python; no C/C++/Rust/Go/Kotlin/Java source | No native C inference/runtime implementation exists in this repo. |
| License | `VERIFIED` | GitHub `licenseInfo=null`; no license/notice/copying file in current tree | Public visibility does not grant reuse rights. Earlier license wording is unresolved; retain the existing legal-review gate. |
| Releases | `VERIFIED` | GitHub Releases API returned zero releases | There are no published Ternuxx release artifacts or verified download links. |
| Product website | `VERIFIED` | No website source in this repo; GitHub Pages API returned 404 | Existing `guides` URLs must not be presented as a working product site. |
| CI | `VERIFIED` | `.github/workflows/repo-contract.yml`, `repo-knowledge-sync.yml`; latest repository-contract/sync runs succeeded | CI validates schemas/README bridge and records honest unknown product build/test state. It does not build/test the application. |
| Dependencies | `PARTIALLY_VERIFIED` | `requirements-dev.txt` has PyYAML; GitHub Actions use major-version tags | No runtime dependency lock, SBOM, build/packaging workflow, or product dependency inventory is present. |
| Public repo history | `VERIFIED` | Five commits: three Sobuj-authored, two Actions bot sync commits | Git authorship alone does not establish full code/asset ownership. |

### Current local worktree

The audit did not reset or clean the checkout. At start, the following documentation was already modified/untracked from earlier authorized readiness work: `CURRENT_STATE.md`, `PROJECT_CLASSIFICATION.yaml`, `README.md`, `docs/RESEARCH.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/architecture/`, `docs/readiness/`, and `docs/testing/`. This report and follow-up changes are additional documentation. No commit or push occurred.

## 2. Existing Ternuxx feature inventory

| Capability | Status | Source/evidence | Audit finding |
|---|---|---|---|
| CLI dispatch/help/version | `PARTIAL` | `bin/ternuxx`, `lib/core.sh`, `lib/help.sh` | Bash lazy-loading CLI exists. Standalone `ternuxx` is only a notice, not the full dispatcher. Help is materially stale. |
| Native install | `IMPLEMENTED_UNQUALIFIED` | `lib/phases.sh` | Default command previews; `install --yes` can run a constrained APT install. It rechecks official repo candidates and blocks removals/upgrades, but has never been device-qualified. Do not run it during this audit. |
| Native desktop | `IMPLEMENTED_UNQUALIFIED` | `lib/desktop.sh`, `lib/desktop-supervisor.sh` | Start/stop/restart/status launch Termux:X11 + XFCE, maintain state/logs, and signal recorded PIDs. Not tests/device-qualified; exact X11/DBus/XFCE process-tree cleanup remains open. |
| Doctor/info | `PARTIAL` | `lib/doctor.sh`, `lib/info.sh` | Readiness and device reporting exist, but this is not a complete recovery system. Some reporting probes may invoke renderer/Vulkan tools; not executed here. |
| Shared application services/API | `NOT_IMPLEMENTED` | No API server, service/domain layer or API schema in source | CLI currently carries behavior directly. No Web/X11 client contract exists in implementation. |
| Capability/permission manager | `NOT_IMPLEMENTED` | No adapters/registry in source | No runtime authorization checks for Termux:API, Boot, Shizuku, or Accessibility. |
| Boot/service orchestrator | `NOT_IMPLEMENTED` | No boot/service registry implementation | Termux:Boot integration and profiles are documented targets only. |
| Web Visualizer | `NOT_IMPLEMENTED` | No frontend/backend/dashboard files | No HTTP listener exists in Ternuxx source. |
| X11 management GUI | `NOT_IMPLEMENTED` | No GUI source/toolkit dependency | Termux:X11 app is installed, but XFCE packages and the manager GUI are absent. |
| PRoot provider/hybrid routing | `NOT_IMPLEMENTED` | No PRoot adapter or dispatcher in Ternuxx `lib/` | Existing Ternux remains separately operated. |
| Recovery/backups/migrations | `NOT_IMPLEMENTED` | No recovery journal or backup/restore code | Operational guides are not implementation evidence. |
| Model library/inference/gateway | `NOT_IMPLEMENTED` | No model/runtime/gateway source in Ternuxx tree | Do not infer a Ternuxx AI capability from external Ternux support. |
| Test/evidence engine | `NOT_IMPLEMENTED` | No product `tests/` directory/build/test command | Documentation has a feature matrix and report templates; no product-generated reports/data. |
| Extension registry | `NOT_IMPLEMENTED` | No extension registration/permission contract | Do not expose untrusted extensions with shell/network/file authority by default. |
| Website/commerce | `NOT_IMPLEMENTED` | No site, payment backend, service catalog or release workflow | Readiness documents are planning only. |

### Source-level defects and risks (not executed)

1. `lib/help.sh` says `start`, `stop`, and `restart` are stubs and says `install --yes` is preview-only. The source paths start/stop processes and install packages. This can lead users to invoke consequential commands under a false safety assumption. Correct help and behavior before distribution.
2. `nt_json_object`/`nt_json_array` manually interpolate JSON strings without escaping. `nt_state_set` interpolates key/value into Python source. The latter has no call sites in the current command tree, but both are unsafe foundations for future shared APIs; replace with a real encoder/structured state library before consumers rely on them.
3. The desktop supervisor tracks the DBus/XFCE launcher PID, not an explicitly owned process group. The existing P2 evidence already identifies descendant cleanup as unverified. Test startup failure, repeat start/stop, unrelated sessions and orphan behavior in fixtures before device work.
4. The installer prints candidate versions but applies package names, so transaction revalidation and repository state need a documented race/atomicity review. It has no validated rollback of partially installed packages.

These are static source-review findings. No CLI command, package transaction, desktop lifecycle, renderer probe, or test suite was run in this audit.

## 3. Current device and execution environment

Read-only observations made from the current Debian 13.7 ARM64 PRoot session at 2026-10-17; no ADB client command was available in `PATH`. Device facts were read through the existing Termux `getprop`, `pm`, and Termux `dpkg-query` interfaces. An ADB server process existed, but no ADB transport/package query was performed.

| Fact | Observed | Evidence boundary |
|---|---|---|
| Current agent runtime | Debian GNU/Linux 13.7, aarch64, PRoot-Distro kernel string | Confirms this agent session runs in a PRoot userland; it does not authorize guest modifications. |
| Device | Xiaomi `[redacted device serial]`, codename `onyx`, Android 16, ABI `arm64-v8a`, SoC `SM8735` | Read-only system properties; no identifying serial was recorded. |
| GPU visibility | `/dev/kgsl-3d0` present and readable model `Adreno825`; `/dev/dri/renderD128` absent in this process context | Detection/access only; this is not an inference or renderer test. |
| APK presence | `com.termux`, `com.termux.boot`, `com.termux.api`, `com.termux.x11`, and `moe.shizuku.privileged.api` resolve through `pm path` | Package presence only; versions, current service state and authorization were not verified. Accessibility-service settings were not inspected. |
| Termux packages | `termux-x11-nightly`, `dbus`, `pulseaudio`, `termux-api` are installed in the native Termux dpkg database | Read-only package status. |
| Native XFCE packages | `xfce4-session`, `xfce4-panel`, `xfce4-settings`, `xfwm4`, `xfdesktop`, `xfconf`, `thunar`, `xfce4-terminal` have no installed records | Current Termux package database, not an install simulation. Native XFCE is not installed. |
| Termux version | `TERMUX_VERSION` is unset in the PRoot environment; app version not retrieved | Earlier dated research records `0.119.0-beta.3`; not revalidated in this audit. |
| Boot scripts | Not inspected | Termux:Boot APK presence does not establish `~/.termux/boot` contents or a Ternuxx boot profile. |
| Shizuku/Accessibility state | Unknown | Shizuku APK is installed; no service connection/authorization was queried. No Ternuxx Accessibility service exists in this repo. |
| Storage/model inventory | Not inspected | Personal/shared storage and model directories were not scanned. |

## 4. Native / PRoot / Android boundary map

| Boundary | Current evidence | Ternuxx integration status | Required constraint |
|---|---|---|---|
| Native Termux | Current package DB and app-presence observations above | Native install and desktop source only; no integration capability manager | Keep native package/process state independent. Never infer Android permission from app/package presence. |
| Termux:X11 | Android companion APK installed; host `termux-x11-nightly` is `1.03.01-6`; no X11 process, X socket, or X lock was present at the 2026-10-17 follow-up check | No manager GUI and native XFCE packages absent | Android APK version, concurrent server/session support, activity routing, and one-vs-two display behavior remain unverified. |
| Debian PRoot | Current agent executes inside Debian 13.7 ARM64 PRoot; separate Ternux GitHub repo is public | No Ternuxx adapter | Preserve Ternux rootfs, launcher, workload and lifecycle. Route explicit commands only through a reviewed adapter. |
| Android integrations | Boot/API/Shizuku APKs installed; Termux API package installed | No adapters/capability registry | Per-operation availability, scope, consent, authorization and revocation must be checked at execution time. |
| Shared files | Not examined | No explicit workspace bridge | No broad `$HOME`, `.ssh`, `.config`, or shared-storage mount; use selected paths only. |
| X11/audio | Termux X11 package and PulseAudio installed | Native lifecycle code starts X11/XFCE; it intentionally does not own audio | Keep host/guest audio lifecycle separate; do not invoke external broad cleanup. |

### Independent Ternux project (external integration candidate)

Read-only review found a local Ternux checkout at `/home/sbj/ternux`, clean at `38a5217` on `codex/license-terms-review-20261016`; this is not `main`, and its cached `origin/main` was behind the live repository. GitHub `soobujmiah/ternux` is public; its live `main` was `9fda63162426f77ee575b5f6729d8799a30f51b7`, and GitHub currently reports Apache-2.0 metadata for that branch. The conclusions below are from public `main` documentation/source, not from running its launcher or rootfs. Ternux's license/third-party inventory was not re-audited here, and no Ternux source or artifact was copied.

- Ternux `main` contains an extensive independent CLI, profile/extension management, native/PRoot graphics and AI support. Its docs describe CPU/Vulkan llama.cpp results, a published CPU/Vulkan extension, an experimental HTP extension, and standalone QNN experiments.
- Current Ternux `lib/desktop.sh` and `lib/phases.sh` include broad `pkill`/PulseAudio stop and wildcard X11/audio socket cleanup paths. Ternuxx must **not** call those generic cleanup/start flows as its lifecycle adapter. Any integration must use a separately reviewed, narrowly scoped external CLI/API contract that cannot trigger these paths inadvertently.
- Static details: Ternux `x` aliases `~/x.sh`; `xgo` opens the Termux:X11 Activity, waits one second, then runs the same launcher. The generated launcher unconditionally kills processes matching `termux-x11` and `virgl_test_server`, kills PulseAudio, and removes wildcard X11/audio sockets both before launch and from its exit trap. It starts Termux:X11 at hard-coded `:0`; the PRoot desktop receives `DISPLAY=:0`. `ternux start` invokes this launcher and may ask before continuing if any `termux-x11` process exists. `ternux stop` broadly kills matching X11/VirGL and PulseAudio processes and removes wildcard sockets. These operations are source-observed only; none was run.
- Ternux `db` and `droot` aliases enter the Debian guest as its ordinary user or root respectively. The aliases are written into the Termux user's shell rc file, so they occupy the same shell namespace where short Ternuxx aliases might otherwise be installed. Do not overwrite these aliases or `x`, `xgo`, and `killx`; prefer a namespaced `ternuxx launch ...` command pending an approved compatibility plan.
- Current Ternuxx native desktop code in `lib/desktop.sh` selects a free-looking display from `:0`–`:10` by checking socket/lock paths and records owned PIDs; it does not coordinate with Ternux's hard-coded `:0` launcher or prove Android activity routing. Its supervisor health and child-process semantics are not device-qualified. This creates a display collision risk for simultaneous sessions.
- The project records examples using `:1` and separates server process state from Android Activity visibility; this is not proof that two servers/sessions can run concurrently or map to separate Android screens on this device. See [ADR-0007](../architecture/decisions/ADR-0007-launch-manager-and-display-ownership.md).
- Existing Ternux Zink/Turnip graphics remains a PRoot desktop/rendering route; it does not automatically qualify every workload, and does not imply a Ternuxx native Termux path.
- The actual Termux-home `~/x.sh` has now been read over the previously authorized localhost SSH connection and matches the broad-cleanup behavior described above. No Ternux launcher command, desktop start/stop, PRoot package action, or rootfs inspection was performed.
- Do not copy Ternux source into Ternuxx. Reuse should mean a versioned provider adapter or supported extension/artifact interface, subject to Ternux's current license, interface stability, owner approval, and no-mutation safety tests.

## 5. AI runtime and provider inventory

| Context/backend | Status | Evidence and limitations | Reuse direction |
|---|---|---|---|
| Ternuxx native CPU inference | `NOT_IMPLEMENTED` | No runtime/model loader/API/test in this repository | CPU remains the free-core baseline; choose a runtime only after license, size, memory and API evaluation. |
| Ternuxx native GPU inference | `UNKNOWN` / `NOT_IMPLEMENTED` | Native Vulkan probe in prior dated research failed `VK_ERROR_INCOMPATIBLE_DRIVER` for that exact Termux setup; no native AI workload | Keep separate from PRoot; evaluate compatible OpenCL/Vulkan runtime only with exact device workload evidence. |
| Ternuxx native NPU | `UNKNOWN` / `NOT_IMPLEMENTED` | SM8735 silicon has Hexagon; no Ternuxx process/runtime/model execution evidence | No claim until an authorized exact-context model workload is verified. |
| Existing Ternux PRoot CPU/Vulkan llama.cpp | `EXTERNAL_DOCUMENTED_EVIDENCE` | Ternux `main` benchmark documentation reports Qwen2.5 1.5B Q4_0 CPU and Adreno Vulkan known-answer `4`; reports 29/29 layers assigned to Vulkan and measured one-device rates. Evidence is dated and not rerun here. | Highest-value reuse candidate: preserve existing runtime and expose it through a narrow Ternux provider adapter; no duplicate llama.cpp runtime initially. |
| Existing Ternux PRoot Hexagon HTP | `EXPERIMENTAL` | Ternux `main` reports a known-answer/31-layer HTP run and 1,389/1,389 HVX `MUL_MAT` cases; HMX has 529 numerical failures, flash-attention has 7 reproduced numerical failures, broad suite has 45 failures then abort. No automatic CPU/Vulkan fallback. | Do not label stable. Integrate only as explicitly experimental with fail-closed selection and visible error/fallback; let Ternux own its extension. |
| Existing Ternux standalone QNN image route | `EXPERIMENTAL` | Reports QNN HTP graph execution in a 25-image SD1.5 run; median 29.76 s/image. Same-seed output repeats but independent tensor correctness and full-resolution review remain open; not packaged as a supported Ternux extension. | Separate research adapter, not a core inference service until independent correctness and performance gates pass. |
| Cloud providers | `NOT_IMPLEMENTED` | No adapter, secret store, router, endpoint or privacy controls | Optional explicit user-configured provider only; no silent local-to-cloud fallback. |

Ternux `docs/BENCHMARKS.md` reports a single-device sequential Qwen2.5 1.5B Q4_0 comparison: CPU `59.04` prompt / `2.38` decode tok/s, `264.39 s` total; Adreno Vulkan `92.19` / `13.27` tok/s, `71.30 s`; conservative HVX HTP `34.20` / `12.02` tok/s, `129.46 s`. Treat these as **Ternux-published, bounded, dated measurements**, not rerun/independently verified by this audit, not sustained/thermal qualification, and not Ternuxx results. The HTP configuration was slower than Vulkan in that run. Ternux docs distinguish this text benchmark from the QNN SD1.5 image pipeline.

Sources are linked from the Ternux repository: [accelerator release plan](https://github.com/soobujmiah/ternux/blob/main/docs/ACCELERATOR-RELEASE-PLAN.md), [benchmarks](https://github.com/soobujmiah/ternux/blob/main/docs/BENCHMARKS.md), [experimental HTP guide](https://github.com/soobujmiah/ternux/blob/main/guides/llama-htp-experimental.md), and [QNN discovery](https://github.com/soobujmiah/ternux/blob/main/experiments/qnn-native/README.md). Those records belong to the separate Ternux project; they do not qualify Ternuxx releases.

## 6. GUI feasibility assessment

| Option | Fit | Main risks/costs | Audit recommendation |
|---|---|---|---|
| Mobile Web Visualizer | Best first visual interface; one responsive UI can work in Android browser and X11 browser | Needs a safe local API/session flow; browser-origin/CSRF risks; X11 browser may add large package/RAM cost | Prototype after API/security contracts. Bind loopback; don't make browser a policy owner. |
| GTK X11 client | Matches XFCE/GTK environment and can feel native on desktop | Adds toolkit bindings/package closure and a second presentation client; native XFCE dependency closure is already substantial | Keep as candidate only; compare exact package size, RSS/startup, accessibility and update costs. |
| Qt X11 client | Mature GUI toolkit and broad widgets | Separate large runtime/dependency family; overlap with GTK/Web UI | No evidence currently justifies it. Do not select before comparative smoke test and owner review. |
| Web UI in X11 browser | Reuses Web Visualizer presentation and API client, avoiding a second full UI implementation | Requires supported Termux browser installed; startup/session integration and resource cost need measurement | Most promising way to satisfy X11 graphical access with less logic duplication; whether it meets “preinstalled Desktop GUI” acceptance is an owner/product decision. |
| Current native desktop | `termux-x11-nightly`, app, DBus and PulseAudio present; XFCE packages missing | Launch code untested; API/package docs stale; no GUI product client | First qualify native desktop lifecycle in existing P2 before bundling a management GUI. |

No package size/RAM/startup comparison was run. No GTK, Qt, browser, or GUI dependency was installed. The master prompt's default-install desktop requirement therefore remains an unvalidated cost/compatibility decision, not a current install profile.

## 7. Permission and boot integration inventory

| Integration | Device observation | Ternuxx code | State still unknown |
|---|---|---|---|
| Termux:Boot | Companion APK installed; native `$HOME/.termux/boot` directory absent at follow-up check | No startup orchestrator or boot profile | Android/OEM startup timing and background limits remain unknown. No boot script or startup behavior was run. |
| Termux:API | Companion APK and `termux-api` command package installed | No operation adapters in project | Per-command permission, API signing compatibility, and operation result. |
| Shizuku | APK installed | No Shizuku API client or capability manager | Running state, authorization, scope, revocation/reconnect; do not infer root. |
| Accessibility | No Ternuxx companion/service in this source | Not implemented | We did not inspect global enabled services; no legitimate Ternuxx use case is approved. Treat as out of scope until a specific user-facing need is established. |
| Android system settings/permissions | Read-only `getprop`/`pm` worked in current PRoot | No permission workflow | No settings were opened or changed; no authorization simulated. |
| ADB/Wireless debugging | ADB client unavailable in PATH; server process seen | No Ternuxx ADB integration | No transport, pairing, port or debugging state checked. Wireless ADB remains disabled/unassumed. |

## 8. Security and licensing risk register

| Risk | Severity | Evidence | Required mitigation / gate |
|---|---|---|---|
| Stale help misrepresents mutating commands | High | `lib/help.sh` vs `lib/desktop.sh`/`lib/phases.sh` | Correct user-facing command contracts and safe examples before any installer distribution. |
| Ternux generic cleanup can kill host X11/audio and delete sockets | Critical boundary | Ternux `main` `lib/desktop.sh`/`lib/phases.sh` | Never invoke generic Ternux start/reset/cleanup from Ternuxx; design a specific opt-in, tracked adapter and test it against preserved-session fixtures. |
| Unqualified process cleanup/orphan descendants | High | Ternuxx supervisor tracks launcher PIDs; existing P2 evidence | Add process-tree/process-group fixture tests and owner-operated start/fail/stop validation before release. |
| Local dashboard/API browser attack | High | No server yet | Same-origin loopback, Host/Origin validation, CSRF/session token, request limits, shared backend authorization, no arbitrary shell. |
| Shizuku/Accessibility privilege overclaim | High | APK presence only; no adapter | Per-operation capability state and consent; do not use Accessibility for security bypass; Shizuku is not root. |
| Model/provider secret and prompt exposure | High | No secrets store or log policy in code | Separate management/inference APIs; secret storage decision, redacted logs, no implicit cloud route. |
| Unlicensed public source/distribution | High | Public GitHub repo has no recognized license; earlier license wording unresolved | No license change/artifact redistribution until chain-of-title and legal review are approved. |
| External Ternux runtime/proprietary/vendor/model licensing | High | Separate project and binaries/runtime dependencies | Keep provider boundary; review current Ternux license, artifact notices, Qualcomm SDK/runtime terms and model license before distribution. |
| No regression/test/release integrity controls | High | No app tests/build/release workflow, no product release | Introduce tests, provenance, checksums/signing and evidence gates by approved phase. |
| Default GUI exceeds phone resource budget | Medium | XFCE package closure exists in source; not installed/measured | Record exact package install size and memory/startup before making GUI default. |

## 9. Gap matrix and proposed sequence

The acceptance criteria below are proposals for owner review; they do not authorize the corresponding implementation.

| Master phase | Current gap | Priority | Proposed exit/definition of done |
|---|---|---|---|
| 0 — Repository & environment audit | This report consolidates code, remote state, current device facts and external provider boundary; some boot/APK runtime facts intentionally remain unknown. | Current | Owner reviews baseline, key risks and provider reuse path. Do not mark legacy P0–P10 generated phase state from this report alone. |
| 1 — Architecture & security foundations | Three-interface/shared-service proposal exists, but API, state schemas, capability/permission model, service registry, credential handling, threat tests and extension boundary are not owner-approved. | Highest next | Approve ADRs for interface/API shape, service/task/state models, permissions and PRoot adapter boundary; set dependency/RAM budgets and test plan. No listener or GUI implementation yet. |
| 2 — Core management backend & CLI | Existing CLI has direct shell logic, stale help, unsafe JSON/state helpers, no tests, no common service/API contract. | P1 | Preserve CLI commands; correct help; use structured JSON/state; test preview/confirm, process ownership, failures, status and fixtures; shared use cases callable without UI. |
| 3 — Boot & permission integration | Relevant APKs are present but no Ternuxx adapters, capability states, profiles or recovery. | P2 | Add only justified Termux:Boot/API operation first; idempotent profile, runtime permission checks, no duplicate services, visible fail/recovery; Shizuku optional and separately verified. Accessibility requires its own approved use case. Physical-device validation owner-operated. |
| 4 — Full-product Web Visualizer | No API/UI. | P2 | Mobile Bangla/English interface for verified modules; same services; loopback/CSRF/origin security tests; status, tasks, diagnostics and safe plans; gracefully handles unavailable modules. |
| 5 — X11 Desktop GUI | No GUI client, XFCE absent, toolkit/size not measured. | P3 | Select an X11 client approach by comparative evidence; expose same supported services; work with X11 absent gracefully; measure package size/RAM/startup/accessibility. Default profile only after owner accepts budget. |
| 6 — AI runtime & gateway | Nothing in Ternuxx; external Ternux already has CPU/Vulkan and experimental HTP/QNN work. | P2 after Phase 1 | First define/version an external provider adapter and prove noninterference; reuse Ternux runtime rather than copy/rebuild; keep CPU fallback; qualify one model/backend/context with correctness before any claim; gateway/cloud separately consented. |
| 7 — Evidence & recovery | Existing templates/docs only; no generated tests or backups/restore. | P2 | Implement report schema/fixtures and actual-workload provenance; add bounded Ternuxx-owned config backup/restore with dry-run and failure tests; no guest rootfs recovery. |
| 8 — Website & commercial preparation | Readiness docs exist, but no site/release, no license, no download artifact, no approved offer. | P3 | Static preview generated from canonical feature/evidence data; correct legal/licensing source; verified release links; no forms/payments until approved. |
| 9 — Release qualification | No product test suite/build, no Ternuxx releases or device-qualified features. | Final | Traceable build/artifact, test evidence, owner-operated device report, security/accessibility/dependency review, recovery/install evidence and explicit owner release decision. |

## 10. Prioritized implementation proposal (approval gated)

1. **Close the safety/documentation defect first:** update help and CLI command contract so users can see which commands create files, start processes, stop processes, or install packages. Add an explicit confirmation design for consequential operations; do not run these paths now.
2. **Approve management boundaries:** define typed application services, shared state/config schema, capability records, operation/task lifecycle, permission scopes, errors, and a versioned interface used by CLI/Web/X11.
3. **Qualify existing native desktop lifecycle:** fixture tests and process-tree handling first; owner-run device acceptance for start/failure/repeat/stop and unrelated-session preservation. Do not use the existing Ternux launcher.
4. **Design the Ternux external provider adapter:** call only a reviewed stable Ternux CLI/API; require named operation IDs and provider identity; never invoke generic cleanup; record exact version and user consent; read-only status adapter first.
5. **Web UI before a second GUI implementation:** implement the shared dashboard after management API security tests. Then decide whether X11 opens the same web client in a supported browser or gets a thin native GTK/other client; require package/resource measurements first.
6. **AI work:** reuse existing Ternux CPU/Vulkan support as a PRoot provider candidate; keep HTP/QNN experimental and evidence-bound. Separately research native Termux CPU/GPU/NPU. No second gateway/runtime until interoperability is tested and reuse rejected for a documented reason.
7. **Permissions/boot:** start with least-privilege Termux:Boot/Termux:API integration for named workflows. Add Shizuku only for concrete operations; no watchdog or Accessibility service by default.
8. **Launch Manager:** approve a typed launch registry and profiles before adding aliases. Preserve Ternux's `x`, `xgo`, `killx`, `db`, `droot`, and `ternux start/stop` behavior; use namespaced `ternuxx launch` commands as the proposed stable interface. Coordinate display allocation, but support only one managed X server until target-device evidence proves concurrent `:0`/`:1` sessions and Android activity/window routing.

## 11. Audit actions, validation, and non-actions

**Read-only actions completed:** repository status/history/remotes and source tree review; GitHub repo/Actions/releases/Pages metadata queries; Termux `getprop`, exact app-package presence checks with `pm path`, and exact native dpkg package-state queries; public Ternux repo/main and local Ternux source/documentation inspection; and a follow-up authenticated, read-only SSH inspection of the specifically authorized Termux launcher, shell aliases, installed Ternux lifecycle source, package records, and boot directory. No unrelated shared-storage or personal files were accessed.

**Not run:** product CLI commands, test suite, shellcheck, package simulation/install, desktop start/stop, GPU/Vulkan/NPU workload, ADB transport/device query, accessibility settings inspection, Termux:Boot scripts, or website build. There is no product test suite to run. The standard Termux boot directory was checked and absent. No model files, shared storage or personal files were scanned.

**Follow-up launch audit:** read the actual native Termux `~/x.sh` and `.bashrc`, confirmed the installed `ternux` command and its installed `desktop.sh`/alias-writer source, checked Termux package records, and checked the exact `$HOME/.termux/boot` path over the previously authorized read-only SSH session. `x.sh` matches the source-reviewed broad cleanup, uses hard-coded `:0`, starts PulseAudio TCP on loopback port 4713 with anonymous local access, starts the X server, then enters Debian with `DISPLAY=:0`. `.bashrc` defines `x`, `xgo`, `killx`, `db`, and `droot`; `ternuxx` and `ternuxx` commands were absent from Termux PATH. Termux:X11 companion package `termux-x11-nightly` is version `1.03.01-6`; the installed Android app version was not queried. `$HOME/.termux/boot` does not exist at this check. A targeted process/socket query found no Termux:X11/VirGL/PulseAudio process, X socket, or X lock then. No command capable of launching/stopping a desktop or service was run; no display concurrency, Activity routing, or boot timing was tested.

**Not changed:** Ternuxx or Ternux source behavior, repository settings/name, license, PRoot rootfs, Ternux launcher, Android settings/permissions, packages, processes, listeners, payment, DNS, website, releases, or production services. No commit/push.

**Supporting verification:** the repository's prior readiness pass recorded `python3 -m tools.repo_knowledge verify` with zero findings and README/matrix link validation. This master audit itself is documentation evidence and must be revalidated after it is added. Those checks do not qualify product code.
