# Architecture

This document records the current native/PRoot provider boundary and existing workstation direction. The owner has accepted shared CLI, interactive Terminal/TUI, Web, and Graphical UI management through one service in [ADR-0004](architecture/decisions/ADR-0004-three-interfaces-shared-management.md). The TUI provides service-backed views and an allowlisted operation runner with explicit mutation confirmation, a centered three-line header, capability-colored status rows, and category availability counts. The browser Web UI is authenticated and loopback-only, with narrow authorized desktop, managed SSH 8023, and GUI Activity-policy mutations. Its global Recent management activity view reads the bounded recovery operation history; technical API responses are separate, and service log files are not exposed by the current API. The Android Activity policy is scoped to its catalog resource, separate from Linux GUI health status. Its bootstrap secret is copied through the native Termux clipboard when available; clipboard failure does not reveal it unless the operator explicitly requests the terminal fallback. General graphical management and broad configuration coverage remain incomplete. The wider optional AI/cloud/runtime design remains phased proposal material in [Unified workstation architecture](architecture/UNIFIED-WORKSTATION.md), with API implementation status in the [management API contract](architecture/MANAGEMENT-API.md).

This design follows [what I want Ternuxx to become](PRODUCT-VISION.md): a mobile workstation where Native Termux is the host authority and the existing Debian PRoot is the Linux workload environment. CPU is the baseline; GPU and NPU are enabled only for verified device/runtime/workload combinations. Ternuxx directly uses typed proot-distro calls and explicitly hands off Native display/audio plus the selected guest graphics route. It does not invoke or depend on the separate Ternux CLI or its private state files. Full interactive PRoot lifecycle ownership remains unqualified.

## Native Termux desktop

Termux:X11 provides the display server. Native XFCE components and applications run as Termux processes. Whether graphics acceleration works depends on the native Termux Mesa/driver combination and the Android device; the Adreno 825 test recorded in [Research](RESEARCH.md) showed native Termux Turnip rejecting that GPU at the tested package version. Do not advertise native GPU acceleration for that configuration until a live renderer check passes.

Native mode runs compatible Termux packages directly, without entering the Debian guest, and can use Termux APIs for Android-facing actions when the companion app, Android permissions, and API support them. These are potential advantages to validate per workflow, not universal guarantees. It has Termux's package/runtime compatibility limits and no systemd. Package names, API behavior, and support must be verified against current Termux repositories before implementation.

The native GUI session state machine, ownership evidence, stale-record recovery, and its current qualification limits are defined in [Native GUI session lifecycle](architecture/GUI-SESSION-LIFECYCLE.md). The CLI and local management service use the same classifier; unknown ownership is never treated as stopped.

## Existing Debian PRoot integration

The current Ternuxx-owned read-only check on Debian display :1 reports Zink/Vulkan 1.4 on Adreno 825 (MESA_TURNIP), X11 reachable, and authenticated Native PulseAudio reachable. The fixed guest launch environment keeps Native Bionic and Debian glibc libraries separate. A live tx db shell and the Native GUI have been observed together; this does not qualify all shared-rootfs writers or full attach/detach/stop lifecycle behavior.

Ternuxx preserves the existing rootfs, user data, installed packages, legacy aliases, and x.sh/xgo/killx workflows. Routine Ternuxx management does not call the separate Ternux CLI or its broad cleanup. A targeted guest configuration adaptation is permitted only after identifying the exact consumer and capturing ownership, mode, hash, impact, and tested recovery; no package/rootfs replacement or broad profile deletion is part of this integration.

Native Termux GPU evidence is separate. The live `:1` status currently reports Adreno 825 with `Accelerated: yes`; a bounded GL workload rendered with score 561. The stock Mesa fallback reports llvmpipe. Native Vulkan device enumeration is not a draw test, and Native Vulkan rendering remains unverified. VirGL remains an explicit route without a verified guest renderer/workload. NPU execution is unverified. See PRoot GPU reuse, Native graphics/audio ownership, and the dated execution evidence.

## End-to-end Native/PRoot integration

Native and PRoot should be two providers in one workstation flow: Termux:Boot selects the profile; Ternuxx manages the X11/session owner; the app registry routes a task; a scoped workspace carries selected inputs/outputs; Doctor, logs, and recovery report which provider handled each step. `native`, `proot`, and `hybrid` profiles are distinct. Hybrid uses one desktop owner and launches selected Debian GUI/CLI workloads into that display; it does not start a second XFCE session on the same display.

The host-to-guest command bridge passes argv as discrete arguments, with a defined work directory and environment allowlist. File access uses a selected workspace, not a broad mount of Termux home or shared storage. Guest-to-host operations are limited to a documented host API (for example, a user-selected share request); the Debian guest does not receive arbitrary host shell access. Host and guest package managers, D-Bus sessions, and accelerator contexts remain separate.

The existing Debian guest is a first-class Ternuxx workload provider. Ternuxx uses typed direct proot-distro commands and passes only the selected display, authenticated Native audio endpoint, and graphics backend. It does not invoke the separate Ternux CLI or source session ownership from its state files. Current :1 Zink/Turnip renderer and audio protocol checks pass; general task routing, clean guest package installation, and full session lifecycle remain incomplete. Preserve the existing rootfs, launchers, and user workflows; never call broad legacy cleanup.

## Display and audio

Termux:X11 is the Android-facing X server and Native Termux owns the Ternuxx :1 graphical session. Native graphical clients use Native libraries; Debian guest applications use their guest Mesa/Turnip libraries while connecting to the selected Native display. Ternuxx owns its PulseAudio server in Native Termux and passes an authenticated loopback endpoint and private cookie to its guest clients. The two ABI/runtime environments remain separate, and service lifecycles are not duplicated inside Debian.

## Termux host integrations

Termux:Boot, Termux:API, and Termux service supervision are optional integrations owned by the Android/Termux host. A runit-based service manager can supervise Native workstation processes but cannot grant Android shell privileges or enable protected debugging settings. Production boot delivery is not currently qualified or enabled. If enabled later, one Native owner starts the :1 desktop/audio services and only then routes selected Debian workloads into that session; it must not start a competing XFCE or PulseAudio owner. Ternuxx uses its direct typed PRoot integration rather than a separate Ternux CLI adapter. Android Activity visibility remains separate from Linux server readiness.

## State ownership

Ternuxx application state belongs under its Native Termux state/config directories. Existing Debian data and packages remain preserved. Ternuxx may manage its own Native service/session state and explicit typed operations against the selected Debian guest; that does not authorize broad cleanup or control of a foreign display/session. A targeted guest config change needs exact ownership/mode/hash pre-state, a bounded impact assessment, and a tested rollback path.

## CPU, GPU, and NPU tiers

- **CPU:** baseline execution path. Record architecture, thread limits, memory use, thermal behavior, and workload performance before recommending settings.
- **GPU:** report native Termux and Debian PRoot as separate process contexts. The current Debian PRoot Zink/Turnip path is a first-class Ternuxx handoff and was live renderer-verified on :1. Native Termux GPU failure does not invalidate the guest route. VirGL remains a separate preserved option without current renderer qualification.
- **NPU:** optional backend behind a feasibility gate. Verify exact SoC/device, supported vendor runtime or delegate, Android/API integration, ABI, model/operator coverage, and actual delegate selection. An NPU in a product specification is not proof of access from Termux or PRoot.
- **Workstation claims:** performance claims require reproducible workload evidence including output correctness, selected backend, cold/warm latency, throughput, memory, and thermal/power behavior. Do not claim acceleration based on the presence of hardware or libraries.

Android's NNAPI is deprecated as of Android 15, so new NPU research should evaluate current vendor runtimes and framework delegates rather than making NNAPI the architectural foundation. See [Research & Evidence](RESEARCH.md#11-cpu-gpu-and-npu-runtime-research).


## SSH access from both providers

The Termux host and Debian PRoot guest may each run an independently managed OpenSSH service. The CLI and GUI are clients of the same host-side service manager, while the PRoot-local CLI is scoped to guest services. Provider-specific identity, credentials, config, logs, listener, and boot profile stay separate. PRoot shares the host network namespace, so each service needs a distinct port and explicit bind scope. SSH is an optional access path and is not required for desktop startup. See [Native/PRoot end-to-end integration](HYBRID-INTEGRATION.md).

## Native Windows compatibility runtime

Wine/Hangover is an optional native Termux application provider, managed independently from Debian PRoot. The package index shows a Hangover 11.16 candidate set, but nothing is installed or app-qualified. The initial scope is a preview-first package plan, per-app Wine prefixes, and architecture-aware compatibility checks. x86 translation, Windows GUI/input/audio, OpenGL, and Vulkan each need workload evidence. Native DXVK remains blocked by the recorded native Vulkan incompatibility; the existing PRoot Zink/Turnip route does not transfer to native Wine. NPU is not part of Wine/Hangover by default and requires a separate Android runtime bridge with a proven inference workload. See [Native Wine and Hangover](WINE-NATIVE.md).

## Workload optimization

Optimization is workload-scoped and evidence-based. Native and PRoot profiles remain separate; controls are limited to settings the chosen app/runtime supports, such as worker count, memory/batch limits, render quality, and concurrency. Thermal and battery telemetry is consumed only from a supported Android/Termux source, otherwise shown as unavailable. Ternuxx does not force CPU/GPU clocks, disable thermal protections, or perform broad rootfs cleanup. See [Workload optimization](OPTIMIZATION.md).


Native graphical and audio ownership, readiness evidence, and the unqualified PRoot endpoint boundary are documented in [Native graphics and audio](architecture/NATIVE-GRAPHICS-AUDIO.md).


## Shared graphics provider diagnostics

`graphics.provider.status` and `graphics.provider.verify` use the same typed management service for Native Termux and the existing Debian PRoot. Native Bionic and Debian glibc results remain separate. Native GL status checks the current display renderer; native OpenGL verification runs the bounded off-screen `glmark2` workload. Vulkan status is device enumeration only and is never labeled as a rendered workload. GLES verification reports unavailable until a dedicated GLES runner is available; the shared OpenGL benchmark is not used as a GLES substitute. The Debian provider uses the existing fixed read-only guest verifier for its configured Zink/Turnip GL path. CLI, TUI, Web, and GTK expose these same operations; no interface owns independent graphics policy.
