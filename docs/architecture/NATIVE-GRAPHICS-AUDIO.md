# Native graphical and audio resource ownership

## Management boundary

Native Termux owns the host package executables, Termux:X11 integration, the native XFCE/D-Bus session, and host audio endpoints. Ternuxx's shared management service owns the native GUI lifecycle and its identity-checked session record. Android Activity visibility is separate from Linux display/session health; read-only GUI status never requests an Activity or polls Android focus. Optional Activity monitoring is defined separately in [GUI monitoring policy](GUI-MONITORING-POLICY.md).

Ternuxx does not claim ownership of a process because it is visible. A service must have a verified identity, lifecycle authority, and readiness check before Ternuxx may start, stop, or restart it. Owner direction makes Native Termux/Ternuxx the PulseAudio service owner and Debian PRoot its client. PulseAudio has an independent lifecycle from the X11 supervisor so `tx stop` cannot disconnect active PRoot audio. Readiness probes target an explicit loopback endpoint, avoiding local daemon autospawn. The managed server configuration is generated privately from the installed Native `default.pa`, without rewriting the owner-modified package file.

## Current Native Termux evidence

The 2026-10-19 device audit found:

- Native Termux GUI session `:1` with recorded live supervisor, Termux:X11, XFCE, and window-manager processes. XFCE has a private D-Bus session address and the Ternuxx XFCE runtime directory. Independent Android visibility remains unknown.
- Installed PulseAudio 17.0-dirty and `pactl` are available. A manual `pactl info` observation during the earlier audit connected to a local server at a Termux private temporary socket and reported `OpenSL_ES_sink`; the sink was `IDLE` at inspection. Doctor no longer repeats that probe because the installed libpulse family did not expose evidence that the attempted autospawn suppression setting is honored. Protocol readiness does not prove audible playback.
- The PRoot workload environment is not qualified to consume this socket. The inspected PRoot wrappers do not set `PULSE_SERVER`; the socket bind, cookie/authentication, Debian client compatibility, audio playback, and path lifetime remain unverified.
- Existing PRoot GUI paths include an explicit `:0` workflow and a separately documented app handoff to `:1`. These must not be conflated. Debian rootfs, packages, workspace, launchers, and acceleration configuration remain guest-owned and are preserved.

See [the dated device audit](../evidence/2026-10-19-native-monitoring-shizuku-graphics-followup.md) for command-level facts and limits.

## Requested boot-ready shared service model

The intended operator model is: Termux starts only resources the owner has enabled for boot, then Ternuxx reconciles each resource to one healthy instance. CLI, TUI, Web UI, and graphical UI call the same management API and catalog for adding/removing resources, start/stop/restart, foreground/background mode where supported, enable/disable, autostart-at-boot, validated configuration, dependency/order inspection, health, logs, and recovery previews. SSH services are part of this scope: an owner should be able to add a separately identified managed SSH endpoint, configure its bind/authentication policy, run it under the selected supervisor in the background, opt it into boot startup, inspect health/logs, disable it, or remove its managed definition. Port 8022 remains the manually managed development resource and must stay outside managed SSH operations; port 8023 remains the existing Ternuxx-managed instance.

A resource already healthy is an idempotent no-op; a startup in progress is not duplicated; one resource has one authoritative supervisor/owner record; conflicting or unowned processes are reported and preserved. Configuration changes and removal must be previewable and reversible, and must not delete package-owned binaries or runtime state. CLI/TUI/Web/GUI are clients of the same lifecycle core, not independent service managers.

The catalog must stay organized as it grows. Every resource has a stable category, display name, short purpose, ownership/supervisor, tags, and capability summary. Initial categories include SSH/access, graphical desktop, audio, boot/startup, Android integrations (optional Shizuku), and PRoot/workloads; deployment-managed servers and applications appear under their own service/workload category. The category names and resource IDs are shared across all interfaces. Users can list by category, search by name, and see only actions valid for that resource. Common tasks need concise guided flows, while advanced configuration remains explicit and validated. Destructive actions such as remove, migration, or disruptive restart show affected dependents and a reviewable preview before execution.

This complete service catalog is a target requirement, not a verified current capability. Current managed service coverage is narrower; the 8023 SSH service is runit-managed and Native PulseAudio has a separate identity-checked lifecycle. Boot profile configuration is not proof that every enabled service has actually reached readiness after Android boot. Optional audio failure must not block GUI readiness.

## Dependency and lifecycle rules

The validated native desktop startup owns its supervisor, X server, XFCE session, and session D-Bus. The X server must become ready before XFCE is considered operational; the session record and process-start identities are reconciled together. A display process alone does not prove a usable desktop.

Owner direction for this qualification: Native Termux/Ternuxx is the sole PulseAudio service owner; Debian PRoot is a client of that Native service. Audio startup/readiness is a separate dependency from GUI readiness, and audio failure must not restart the GUI or terminate unrelated guest processes. The endpoint is `tcp:127.0.0.1:4713`; Ternuxx derives an authenticated config using the Native cookie and binds only IPv4 loopback. Native Bionic and Debian glibc clients remain separate; do not copy host libraries into the guest. Actual PRoot playback still requires live qualification.

## Remaining implementation gates

- Extend the shared management core from the existing GUI/8023 SSH slices to a persistent, validated service catalog with idempotent singleton enforcement, opt-in boot readiness, and consistent add/remove/configure controls across CLI, TUI, Web UI, and GUI. The live monitor policy is shared; general service CRUD parity is not yet qualified.
- Verify the Native-owned PulseAudio lifecycle on-device: exact process identity, singleton/start-in-progress handling, stale owned-state recovery, bounded authenticated readiness, logs, and safe stop semantics. Preserve and report live/unknown foreign processes and locks; never unlink them. The managed config is generated privately from Native `default.pa`; the owner-modified package file remains unchanged.
- Pass the Native cookie path and loopback endpoint to Ternuxx-launched Debian clients only. Test the Debian client protocol and playback without replacing guest libraries or enabling wildcard ingress.
- Add collision tests for live, stale-owned, malformed, and foreign PulseAudio state, plus concurrent `tx db` and Native `tx gui` operation. Audio service failure must not block CLI/X11 startup; actual audio readiness/playback must be reported separately.
- Model D-Bus/XFCE dependencies and readiness in one lifecycle core. Do not start a second D-Bus/XFCE session on a display already owned by another manager.
- Qualify graphical workloads and audio output separately; package presence, socket existence, renderer strings, or process existence alone are not parity evidence.


## Implementation checkpoint — 2026-10-20

Native PulseAudio is now started and identity-managed by Ternuxx through `tx audio`; the installed package `default.pa` remains untouched. A private managed config changes only the inspected loopback anonymous listener to cookie-authenticated loopback. Native status and explicit TCP `pactl` probes passed; Ternuxx-managed Debian one-shot `tx db` received the endpoint and cookie path and its `pactl info` succeeded. A silent bounded guest PCM stream was accepted by the server, but human-audible output remains unverified. `tx stop` deliberately does not stop PulseAudio. The existing `:1` desktop and interactive PRoot PID 14360 remained live during the checks. Full regression suite: 547 passed, exit 0. Exact commands and limitations are in [the current execution evidence](../evidence/2026-10-20-workstation-qualification-execution.md).

The earlier 2026-10-19 observations above are historical snapshots. Remaining audio qualification is: lifecycle concurrency/stress, safe owner-mediated stop/restart while checking active clients, audible output, and management UI status/action parity. Do not infer audio health from GUI readiness. CPU/GPU/NPU qualification is reported separately through the read-only management resource; no acceleration workload claim is added here.


The isolated PRoot audio verifier originally omitted the Native cookie, so its guest status incorrectly reported audio unavailable while ordinary `tx db` `pactl` worked. The verifier now validates and binds only the private cookie file at a fixed guest path for its read-only status request. A repeated `tx proot verify` on `:1` reports guest audio reachable alongside Zink/Turnip. This single-file diagnostic handoff does not expose HOME or alter Debian config. See the superseding 2026-10-20 execution record for exact result and limitations.


## Current Ternuxx handoff evidence — 2026-10-20

Native Termux owns the display and PulseAudio server. Ternuxx strips the Android ART/classpath/storage variables that proot-distro would otherwise persist in its generated profile and passes the guest display, authenticated PulseAudio cookie/server, and selected graphics route explicitly. Debian PRoot :1 verified Zink/Turnip Adreno 825 with accelerated GL and Native PulseAudio protocol reachability. Native GTK process startup is live, but Native Vulkan logged `VK_ERROR_INCOMPATIBLE_DRIVER`; visual usability and NPU execution remain unverified. The generated Debian profile is still written by the installed proot-distro package; Ternuxx does not patch that package or copy Bionic libraries.
