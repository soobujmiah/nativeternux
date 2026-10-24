# Native and PRoot end-to-end integration

> **Historical record, superseded 2026-10-24.** Ternuxx is Native Termux-only. PRoot implementation and operations described below have been retired and must not be used as current setup instructions. Current behavior is documented in [the product vision](PRODUCT-VISION.md), [phase status](PHASE-STATUS.md), and [Native-only retirement audit](evidence/2026-10-24-native-only-proot-removal-audit.md).

**Document status (rechecked 2026-10-23):** This contains current provider-boundary requirements plus older proposed workflows. Follow current CLI help, phase status, and the capability matrix for implemented commands. The cross-provider SSH CLI and boot-profile sketches below are not current features. The owner-approved full-repository task separately permits exact, previewed, and reversible Native/existing-Debian config changes.

Native Termux is the primary workstation and authoritative owner of native SSH, native services, boot recovery, lifecycle, and persistent continuity evidence. The existing Debian PRoot is an integrated but independently managed development/execution provider. They keep separate package managers, runtime libraries, configuration, and ownership; Ternuxx connects them through explicit, narrow interfaces. Native boot and recovery must work with PRoot stopped, unavailable, or without an agent running inside it.

## End-to-end flow

```text
Android boot → Termux:Boot
   │ native orchestrator (does not enter PRoot or wait for its agent)
   ▼
Native Termux manager ── native SSH, services, Doctor, continuity journal, recovery
   ├── Termux:X11 + selected desktop session (optional)
   ├── Native apps + Termux:API actions
   └── Existing Debian PRoot provider (optional, independently managed)
          ├── existing Debian graphics stack and Linux applications
          └── selected workspace + bounded, authorized workload requests
```

Native recovery and selected native services run independently. A separate optional profile may request a desktop or PRoot workload after native readiness; failure of that optional work does not fail native SSH or continuity recording. The table shows design choices; PRoot/hybrid boot-profile support remains blocked pending ownership-safe startup integration. The desktop choice is:

| Profile | Desktop owner | PRoot use | Display policy |
|---|---|---|---|
| `native` | Native XFCE in Termux | Available for selected guest workloads | One native XFCE session on the managed X11 display |
| `proot` | Existing Debian XFCE session | Existing Debian desktop and workload route | Guest desktop on the managed X11 display, using the Ternuxx-managed Debian display/audio handoff |
| `hybrid` | Native XFCE in Termux | Guest applications and jobs on demand | One desktop session; do not launch a second XFCE against the same display |

The `proot` and `hybrid` rows describe optional workload/desktop choices, not boot prerequisites. Starting both full desktop sessions simultaneously requires an independently validated second display and explicit resource/ownership handling. Ternuxx’s canonical first-party Debian command is `tx db`. The Native `db`/`droot` aliases now delegate to its regular-user/root paths after an owner-authorized migration; the `x`/`xgo` convenience aliases and `~/x.sh` wrapper remain as inventoried in [the entrypoint decision evidence](evidence/2026-10-22-legacy-entrypoint-inventory.md). Shell changes require explicit authorization and rollback; see [current alias migration evidence](evidence/2026-10-23-native-legacy-alias-migration.md).

## Integration matrix

| Boundary | Host-to-guest path | Guest-to-host return path | Rule |
|---|---|---|---|
| Boot and services | Termux:Boot starts the native orchestrator and native-owned services first; it may then request an explicitly selected PRoot workload | Native continuity/status is recorded even if PRoot is unavailable; optional guest results return with status, logs, exit code, and operation ID | PRoot never gates native recovery. Never run an interactive GUI launcher as a boot command. `tx db` is the managed CLI path; the current `db`/`droot` aliases delegate to it, while the `x`/`xgo` launch wrappers remain separately scoped. |
| SSH access | Native Termux `sshd` and Debian PRoot `sshd` have separate service identities, configs, host keys, authorized-key files, ports, and boot settings | Each endpoint reports its own listener, auth mode, clients (when safely observable), logs, and lifecycle state | Same Android network namespace: reserve distinct ports and report bind address. Default loopback; LAN access is explicit opt-in. CLI and GUI use one shared manager. |
| Commands and apps | Native CLI selects a provider and passes argv, work directory, and an allowlisted environment to a guest command | Streamed output, result files, exit status, and signal status return to the caller | No shell-string concatenation or arbitrary guest-to-host shell execution. |
| Files | Bind only a Ternuxx workspace or a user-selected input/output path | Guest outputs land in the selected workspace; Termux:API can share a chosen file | No blanket `/sdcard`, Termux home, SSH key, or `.config` access. Bind read-only for inputs where practical. |
| Display | Native clients and guest GUI apps connect to the selected Termux:X11 display | Display readiness and GUI visibility are reported independently | A single XFCE owner per display. Guest X11 clients use the host display socket through the supported shared-tmp/X11 mechanism. |
| Audio | Native Termux owns PulseAudio when it starts it; guest clients receive the configured endpoint | Playback errors and process state return to Doctor/logs | One service owner. Stop only a service Ternuxx started and recorded. |
| Android APIs | Native Termux calls supported Termux:API commands after user action/permission | Result is returned to native CLI/UI; a selected result can be handed to PRoot | Do not expose API app credentials or arbitrary Android broadcasts inside the guest. |
| GPU/NPU | Native and guest workloads choose their own verified runtime/backend | Each result records provider, renderer/delegate, and workload proof | Debian Zink/Turnip remains a guest-process route; it does not establish Native GPU support. The separate Ternux project is reference-only and its CLI/state are not runtime dependencies. NPU remains unclaimed until proven per context. |
| Packages/catalog | Installer declares `termux` or `proot-debian` target and previews that package manager's exact transaction | Installed app metadata is recorded per provider | Never use apt to install across the host/guest boundary; optional app removal cannot prune the guest or base desktop. |
| Optimization | Select a profile and controls for the chosen provider/workload | Metrics, baseline comparison, thermal state, and restore status are reported | No silent cross-provider fallback, system clock changes, or thermal-protection bypass. |
| Doctor/recovery | Host manager gathers read-only findings from both environments | One report labels each finding's provider and owner | Repair/restore operates only within the explicitly selected Ternuxx-owned target. Existing Debian guest state needs a task-specific preview, backup, explicit apply, and tested rollback before migration. |

## Independent SSH services and controls

The Termux host SSH service and Debian guest SSH service are separate providers. The host service runs as the Termux app user; the guest service runs as the selected Debian PRoot user. They have separate configuration, host identity keys, authorized client keys, logs, boot enablement, and tracked process identity. The same SSH client may reach both endpoints, but each endpoint has its own configured address and port. PRoot does not provide a separate network namespace, so a port conflict is global to both services.

ADB is also provider-scoped: the owner reports that its binaries are in PRoot, not native Termux, and that its Wireless Debugging connection plus a custom Shizuku watchdog currently restart Shizuku after reboot. This is owner-reported runtime behavior; exact fork/build and boot behavior have not been inspected. The future PRoot ADB server on TCP 5037 and Android's Wireless Debugging `adbd` endpoint are different connections: 5037 is the local ADB client-to-server port, while Wireless Debugging uses a separate device endpoint. So an ADB server on 5037 does not itself preserve the Wireless Debugging endpoint or replace Shizuku. The Ternuxx management TCP API is a third, separate service. ADB discovery must first inventory the selected guest read-only; if an ADB server is later enabled, its default is loopback-only, explicit opt-in, and no boot auto-start. Neither ADB reachability nor SSH login grants Ternuxx management authorization. See [ADR-0014](architecture/decisions/ADR-0014-proot-adb-and-management-tcp.md) for implementation gates and management service requirements.

Native SSH management currently uses the fixed Ternuxx service on loopback port 8023.

Commands: tx ssh inspect; tx ssh start (read-only preview); tx ssh start --yes --plan-id PLAN_ID (apply the exact preview).

Guest SSH on Debian remains separate; the cross-provider --provider commands proposed in the original design are not implemented. The Native CLI can inspect Native SSH and inventory/verify PRoot, but it does not adopt or manage an independently configured guest sshd. No CLI running inside Debian is a Ternuxx runtime dependency. Any future guest service control must use a fixed typed operation, exact target, authorization, timeout, and structured result.

The current Web/TUI/GTK clients use shared typed services for implemented actions. Guest SSH settings, key/lifecycle controls, and parity across all clients remain separate P4 work.

Current Native SSH controls use the shared typed service contract across supported clients. Any future Debian guest SSH page must show its provider, state, bind address, port, auth mode, boot policy, and last operation, and use exact preview/confirmation for changes. No GUI may run raw shell text or silently alter guest configuration.

The fixed Ternuxx Native SSH service uses public-key authentication, denies root login, and binds to loopback. Its current profile does not configure Debian guest SSH. Host and guest keys must never be copied or shared automatically; any future LAN listener requires a separate explicit exposure review. Do not put private keys, passwords, or pairing material in Ternuxx logs or backups. If OpenSSH is missing in a provider, keep local GUI/CLI control available and show the package preview for that provider without switching to the other SSH service.

## Shared workspace contract

A future file/workspace bridge should use one clearly named Ternuxx workspace, not the whole Termux home. Commands name input/output paths below that root. A run record stores provider, argv as an array, working directory, environment allowlist, start time, exit result, and output paths. Secrets are not copied across by default. Users can add a deliberate mount later with a preview and read-only option.

## Continuity and resource ownership

Persistent checkpoints and reboot evidence are native-owned and stored in Ternuxx's private Termux storage. A checkpoint must be sufficient to inspect pending work after reboot without preserving an agent process. On reboot, native services recover and report first. Guest operations remain pending until a fresh PRoot session exists and the owner requests continuation. Cross-provider task records include source/target provider, operation ID, bounded request, authorization result, timeout/result status, and sanitized recovery details. They exclude secrets and unnecessary personal paths.

Native and guest process/resource ownership is separate. Stopping PRoot may stop only guest-owned processes and must leave independent native SSH/services healthy. Restarting native services must not mutate guest rootfs/session state. A Wake Lock is attributed to the specific active workload/service that acquired it; another provider or service cannot release it. These are requirements, not verified behavior; acceptance evidence is tracked in [ADR-0010](architecture/decisions/ADR-0010-native-termux-autonomy.md).

## Session and resource ownership

Ternuxx owns only processes it starts through its adapter and never invokes the separate Ternux CLI or broad cleanup as a lifecycle shortcut. Keep the separate Ternux source repository independent. Exact installed guest helpers may be adapted or retired only after caller/workload verification and a Ternuxx-owned preview, backup, explicit apply, and tested rollback. The current `~/x.sh` is a compatibility wrapper to `scripts/proot-x11-app.sh`; its observed behavior and the Native `x`/`xgo` aliases are recorded in [the current entrypoint inventory](evidence/2026-10-22-legacy-entrypoint-inventory.md). It requires an existing Ternuxx display, may start/reuse Native audio, and launches a guest app; it is not a boot helper or a desktop lifecycle manager. Do not infer ownership of a session started through an external alias.

The host owns the X11 server and optional host PulseAudio endpoint for a selected session. The guest gets only the display/audio values and mounts needed by that run. Guest D-Bus stays a guest session; host D-Bus is not mounted into Debian. A guest desktop session and native XFCE session cannot both claim the same display lifecycle.

PRoot does not provide the same PID, network, IPC, cgroup, or security isolation as a kernel container. The manager must describe this as a Linux userland/compatibility layer, not a sandbox boundary. It cannot promise that systemd works inside the guest.

## Historical delivery proposal

The following sequence is retained from the earlier architecture proposal and does not replace the current P0–P10 roadmap or its active P4 phase.

1. **Boot and lifecycle:** native, PRoot, and hybrid profiles; owner tracking; one display/service owner; safe logs and recovery journal.
2. **PRoot parity:** preserve the Ternux Debian rootfs and its exact verified graphics/session environment through a separate adapter; read-only discovery before any command.
3. **Useful bridges:** selected file handoff, native-to-guest argv-safe command dispatch, GUI app launch, audio/display integration, and result return.
4. **Workflow routing:** app catalog and installer show provider; Doctor and optimization report each provider; hybrid workflow rules explain where commands and data run.
5. **Capability proof:** run the same suitable workload in native and PRoot separately, record actual renderer/delegate, correctness, thermal/power state, and limitations. Do not infer parity from one successful layer.

Each device-changing step needs an exact target/impact preview and rollback. The active full-repository task is explicit owner authorization for task-required Native and existing Debian configuration work under those bounds. Add-on APK installs, Android permission changes, and unrelated boot changes remain outside this task.


## Debian GUI modes managed by Ternuxx

The full PRoot XFCE desktop is launched with `tx pgui`. Auto mode selects independent Termux:X11 `:0` when the Native desktop is stopped and nested Xephyr `:2` when Native `:1` is running. Explicit `standalone` and `nested` modes enforce the same lifecycle ownership checks. Native PulseAudio stays on the authenticated loopback endpoint; Debian keeps its own Zink/Turnip glibc stack. The nested desktop is foreground-controlled with Ctrl-C, while standalone has `tx pgui status|stop`. Individual Debian shortcuts remain routed through `tx mng app launch` on Native `:1`. Current device evidence and display/GLX limitations are in [the PRoot GUI report](evidence/2026-10-20-proot-full-gui.md).
