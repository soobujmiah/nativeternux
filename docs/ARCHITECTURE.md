# Architecture

This document records the current native/PRoot provider boundary and existing workstation direction. The owner has accepted shared CLI, interactive Terminal/TUI, Web, and Graphical UI management through one service in [ADR-0004](architecture/decisions/ADR-0004-three-interfaces-shared-management.md). The TUI provides service-backed views and an allowlisted operation runner with explicit mutation confirmation. The browser Web UI is authenticated and loopback-only, with narrow authorized desktop, managed SSH 8023, and GUI-monitoring policy mutations. Its bootstrap secret is copied through the native Termux clipboard when available; clipboard failure does not reveal it unless the operator explicitly requests the terminal fallback. General graphical management and broad configuration coverage remain incomplete. The wider optional AI/cloud/runtime design remains phased proposal material in [Unified workstation architecture](architecture/UNIFIED-WORKSTATION.md), with API implementation status in the [management API contract](architecture/MANAGEMENT-API.md).

This design follows [what I want Ternuxx to become](PRODUCT-VISION.md): a mobile workstation where native Termux and my existing PRoot setup work together. CPU is the baseline; GPU and NPU are enabled only for verified device/runtime/workload combinations. The design has two complementary first-class layers: Termux-native processes for compatible tools and permitted Android/Termux integrations, and the existing Ternux Debian PRoot for its Linux userland, desktop, configured graphics path, and demonstrated workloads. Hybrid mode joins useful workflows across them with scoped handoffs. The `soobujmiah/ternux` project and Debian rootfs remain independently owned; a Ternuxx adapter may reuse that rootfs while owning only process/session instances it explicitly starts and can verify.

## Native Termux desktop

Termux:X11 provides the display server. Native XFCE components and applications run as Termux processes. Whether graphics acceleration works depends on the native Termux Mesa/driver combination and the Android device; the Adreno 825 test recorded in [Research](RESEARCH.md) showed native Termux Turnip rejecting that GPU at the tested package version. Do not advertise native GPU acceleration for that configuration until a live renderer check passes.

Native mode runs compatible Termux packages directly, without entering the Debian guest, and can use Termux APIs for Android-facing actions when the companion app, Android permissions, and API support them. These are potential advantages to validate per workflow, not universal guarantees. It has Termux's package/runtime compatibility limits and no systemd. Package names, API behavior, and support must be verified against current Termux repositories before implementation.

The native GUI session state machine, ownership evidence, stale-record recovery, and its current qualification limits are defined in [Native GUI session lifecycle](architecture/GUI-SESSION-LIFECYCLE.md). The CLI and local management service use the same classifier; unknown ownership is never treated as stopped.

## Existing Ternux PRoot provider

The existing Ternux project documents an Adreno Zink/Turnip path inside Debian PRoot and labels it a measured route. On 2026-10-18, a read-only guest `glxinfo -B` and short draw-loop check on display `:1` selected Zink backed by Turnip and reported `Accelerated: yes`; the existing Ternux-owned `:0` desktop was not active, and the Ternuxx ownership-aware PRoot provider remains unimplemented. The reviewed Ternux launch path binds KGSL/DRM device nodes, sets the guest Mesa environment, and connects guest applications to Termux:X11. Ternuxx can integrate this as an opt-in provider while the legacy Ternux launchers remain available. A Ternuxx lifecycle may reuse the same Debian rootfs, but must have a unique instance record and may stop only its own verified processes; shared-rootfs concurrent use and display conflicts must be checked before enabling start/stop. See [Reusing Ternux's GPU-Accelerated PRoot](PROOT-GPU.md) and [P4 renderer evidence](evidence/P4-proot-gpu-renderer-2026-10-18.md).

This route is not native rendering. The application must execute inside the Debian guest. Native Termux applications continue to use the native graphics libraries. Also, the Ternux launcher owns its display and audio lifecycle and may perform broad cleanup; Ternuxx may start a PRoot session only through the opt-in adapter and may stop only processes that adapter recorded as its own. It must not invoke Ternux cleanup, edit `~/x.sh`, or start two desktop sessions on one display.

Ternuxx must not modify, minimize, upgrade, remove, prune, or silently reinstall the existing `debian` rootfs. Any future isolated rootfs is supplementary and cannot replace or reduce existing Ternux features. A separate Ternuxx-owned rootfs may be considered only for a demonstrated workload gap and requires explicit owner choice.

## End-to-end Native/PRoot integration

Native and PRoot should be two providers in one workstation flow: Termux:Boot selects the profile; Ternuxx manages the X11/session owner; the app registry routes a task; a scoped workspace carries selected inputs/outputs; Doctor, logs, and recovery report which provider handled each step. `native`, `proot`, and `hybrid` profiles are distinct. Hybrid uses one desktop owner and launches selected Debian GUI/CLI workloads into that display; it does not start a second XFCE session on the same display.

The host-to-guest command bridge passes argv as discrete arguments, with a defined work directory and environment allowlist. File access uses a selected workspace, not a broad mount of Termux home or shared storage. Guest-to-host operations are limited to a documented host API (for example, a user-selected share request); the Debian guest does not receive arbitrary host shell access. Host and guest package managers, D-Bus sessions, and accelerator contexts remain separate.

The existing Ternux Debian PRoot remains a first-class provider. A Ternuxx adapter may reuse its reviewed rootfs and Zink/Turnip environment while tracking only the processes it starts. It must not use `~/x.sh` as a lifecycle hook: the inspected launcher runs broad process termination and wildcard socket deletion before startup. It must not rewrite that launcher, perform package operations, or prune the rootfs. See [Native/PRoot end-to-end integration](HYBRID-INTEGRATION.md) for the boundary matrix and delivery sequence.

## Display and audio

Termux:X11 is the Android-facing X server. Both Termux-native clients and PRoot clients can connect to an X display when configured, but each client uses the libraries and graphics driver in its own process environment. In Ternux's documented PRoot route, PulseAudio is hosted by Termux and exposed to guest clients; native and guest session startup must not compete for the same audio service lifecycle.

## Termux host integrations

Termux:Boot, Termux:API, and Termux service supervision are optional integrations owned by the Android/Termux host. A runit-based service manager can supervise Termux-side workstation processes with fewer dependencies; it cannot grant Android shell privileges or enable protected debugging settings. Shizuku is a separate, optional elevated provider and is not needed for desktop or boot management. Boot profiles cover native, PRoot, and hybrid sessions: native starts Termux XFCE; PRoot starts the existing Ternux Debian desktop through a separate Ternuxx-owned adapter; hybrid starts one native XFCE session and routes selected Debian workloads to its display. The PRoot adapter must not use the inspected `~/x.sh` boot path because it broadly kills X11/PulseAudio processes and deletes wildcard sockets. Each profile starts only its declared provider and requests the Termux:X11 activity. Server readiness and visible GUI readiness are reported separately, because Android may restrict bringing an activity to the foreground from a boot task. API features require the matching companion app, supported commands, compatible signing, and any Android permissions. Ternuxx should offer explicit, inspectable opt-ins and keep its base desktop usable when these integrations are absent. Dependency checks choose a named, lower-capability fallback (manual boot, one-shot startup without runit, CLI-only without X11, or unprivileged mode without Shizuku); they never claim a missing APK/package is available or silently switch providers. See [Doctor, management, and recovery](OPERATIONS.md).

## State ownership

Ternuxx state belongs under its own application state/config directories. Existing Ternux files, legacy-managed process state, display sockets, and PulseAudio sockets remain outside Ternuxx cleanup authority. A future Ternuxx PRoot adapter may manage only process/session identities it created and has revalidated; sharing the rootfs does not confer authority over another session.

## CPU, GPU, and NPU tiers

- **CPU:** baseline execution path. Record architecture, thread limits, memory use, thermal behavior, and workload performance before recommending settings.
- **GPU:** report native Termux and Debian PRoot as separate process contexts. The existing Ternux PRoot Zink/Turnip configuration remains an important supported route; live renderer proof must come from the actual guest workload. Native Termux GPU failure does not invalidate that separate route.
- **NPU:** optional backend behind a feasibility gate. Verify exact SoC/device, supported vendor runtime or delegate, Android/API integration, ABI, model/operator coverage, and actual delegate selection. An NPU in a product specification is not proof of access from Termux or PRoot.
- **Workstation claims:** performance claims require reproducible workload evidence including output correctness, selected backend, cold/warm latency, throughput, memory, and thermal/power behavior. Do not claim acceleration based on the presence of hardware or libraries.

Android's NNAPI is deprecated as of Android 15, so new NPU research should evaluate current vendor runtimes and framework delegates rather than making NNAPI the architectural foundation. See [Research & Evidence](RESEARCH.md#11-cpu-gpu-and-npu-runtime-research).


## SSH access from both providers

The Termux host and Debian PRoot guest may each run an independently managed OpenSSH service. The CLI and GUI are clients of the same host-side service manager, while the PRoot-local CLI is scoped to guest services. Provider-specific identity, credentials, config, logs, listener, and boot profile stay separate. PRoot shares the host network namespace, so each service needs a distinct port and explicit bind scope. SSH is an optional access path and is not required for desktop startup. See [Native/PRoot end-to-end integration](HYBRID-INTEGRATION.md).

## Native Windows compatibility runtime

Wine/Hangover is an optional native Termux application provider, managed independently from Debian PRoot. The package index shows a Hangover 11.16 candidate set, but nothing is installed or app-qualified. The initial scope is a preview-first package plan, per-app Wine prefixes, and architecture-aware compatibility checks. x86 translation, Windows GUI/input/audio, OpenGL, and Vulkan each need workload evidence. Native DXVK remains blocked by the recorded native Vulkan incompatibility; the existing PRoot Zink/Turnip route does not transfer to native Wine. NPU is not part of Wine/Hangover by default and requires a separate Android runtime bridge with a proven inference workload. See [Native Wine and Hangover](WINE-NATIVE.md).

## Workload optimization

Optimization is workload-scoped and evidence-based. Native and PRoot profiles remain separate; controls are limited to settings the chosen app/runtime supports, such as worker count, memory/batch limits, render quality, and concurrency. Thermal and battery telemetry is consumed only from a supported Android/Termux source, otherwise shown as unavailable. Ternuxx does not force CPU/GPU clocks, disable thermal protections, or clean the existing Ternux rootfs. See [Workload optimization](OPTIMIZATION.md).


Native graphical and audio ownership, readiness evidence, and the unqualified PRoot endpoint boundary are documented in [Native graphics and audio](architecture/NATIVE-GRAPHICS-AUDIO.md).
