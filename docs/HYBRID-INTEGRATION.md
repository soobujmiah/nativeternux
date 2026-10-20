# Native and PRoot end-to-end integration

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
          ├── existing Ternux GPU environment and Linux apps
          └── selected workspace + bounded, authorized workload requests
```

Native recovery and selected native services run independently. A separate optional profile may request a desktop or PRoot workload after native readiness; failure of that optional work does not fail native SSH or continuity recording. The desktop choice is:

| Profile | Desktop owner | PRoot use | Display policy |
|---|---|---|---|
| `native` | Native XFCE in Termux | Available for selected guest workloads | One native XFCE session on the managed X11 display |
| `proot` | Existing Debian XFCE session | Full existing Ternux desktop/workload route | Guest desktop on the managed X11 display, using the reviewed Ternux environment |
| `hybrid` | Native XFCE in Termux | Guest applications and jobs on demand | One desktop session; do not launch a second XFCE against the same display |

The `proot` and `hybrid` rows describe optional workload/desktop choices, not boot prerequisites. Starting both full desktop sessions simultaneously requires an independently validated second display and explicit resource/ownership handling. Existing Ternux `xgo` and `db` behavior is preserved: `xgo` continues the established graphical workflow, while `db` enters the existing guest without launching a GUI.

## Integration matrix

| Boundary | Host-to-guest path | Guest-to-host return path | Rule |
|---|---|---|---|
| Boot and services | Termux:Boot starts the native orchestrator and native-owned services first; it may then request an explicitly selected PRoot workload | Native continuity/status is recorded even if PRoot is unavailable; optional guest results return with status, logs, exit code, and operation ID | PRoot never gates native recovery. Never run the current broad-cleanup `~/x.sh` as a boot command. Preserve `xgo` and `db` semantics. |
| SSH access | Native Termux `sshd` and Debian PRoot `sshd` have separate service identities, configs, host keys, authorized-key files, ports, and boot settings | Each endpoint reports its own listener, auth mode, clients (when safely observable), logs, and lifecycle state | Same Android network namespace: reserve distinct ports and report bind address. Default loopback; LAN access is explicit opt-in. CLI and GUI use one shared manager. |
| Commands and apps | Native CLI selects a provider and passes argv, work directory, and an allowlisted environment to a guest command | Streamed output, result files, exit status, and signal status return to the caller | No shell-string concatenation or arbitrary guest-to-host shell execution. |
| Files | Bind only a Ternuxx workspace or a user-selected input/output path | Guest outputs land in the selected workspace; Termux:API can share a chosen file | No blanket `/sdcard`, Termux home, SSH key, or `.config` access. Bind read-only for inputs where practical. |
| Display | Native clients and guest GUI apps connect to the selected Termux:X11 display | Display readiness and GUI visibility are reported independently | A single XFCE owner per display. Guest X11 clients use the host display socket through the supported shared-tmp/X11 mechanism. |
| Audio | Native Termux owns PulseAudio when it starts it; guest clients receive the configured endpoint | Playback errors and process state return to Doctor/logs | One service owner. Stop only a service Ternuxx started and recorded. |
| Android APIs | Native Termux calls supported Termux:API commands after user action/permission | Result is returned to native CLI/UI; a selected result can be handed to PRoot | Do not expose API app credentials or arbitrary Android broadcasts inside the guest. |
| GPU/NPU | Native and guest workloads choose their own verified runtime/backend | Each result records provider, renderer/delegate, and workload proof | The Ternux Zink/Turnip route stays a guest process route; it does not become native GPU support. NPU remains unclaimed until proven per context. |
| Packages/catalog | Installer declares `termux` or `proot-debian` target and previews that package manager's exact transaction | Installed app metadata is recorded per provider | Never use apt to install across the host/guest boundary; optional app removal cannot prune the guest or base desktop. |
| Optimization | Select a profile and controls for the chosen provider/workload | Metrics, baseline comparison, thermal state, and restore status are reported | No silent cross-provider fallback, system clock changes, or thermal-protection bypass. |
| Doctor/recovery | Host manager gathers read-only findings from both environments | One report labels each finding's provider and owner | Repair/restore operates only within the explicitly selected Ternuxx-owned target. Existing Ternux state needs separate consent and backup. |

## Independent SSH services and controls

The Termux host SSH service and Debian guest SSH service are separate providers. The host service runs as the Termux app user; the guest service runs as the selected Debian PRoot user. They have separate configuration, host identity keys, authorized client keys, logs, boot enablement, and tracked process identity. The same SSH client may reach both endpoints, but each endpoint has its own configured address and port. PRoot does not provide a separate network namespace, so a port conflict is global to both services.

ADB is also provider-scoped: the owner reports that its binaries are in PRoot, not native Termux, and that its Wireless Debugging connection plus a custom Shizuku watchdog currently restart Shizuku after reboot. This is owner-reported runtime behavior; exact fork/build and boot behavior have not been inspected. The future PRoot ADB server on TCP 5037 and Android's Wireless Debugging `adbd` endpoint are different connections: 5037 is the local ADB client-to-server port, while Wireless Debugging uses a separate device endpoint. So an ADB server on 5037 does not itself preserve the Wireless Debugging endpoint or replace Shizuku. The Ternuxx management TCP API is a third, separate service. ADB discovery must first inventory the selected guest read-only; if an ADB server is later enabled, its default is loopback-only, explicit opt-in, and no boot auto-start. Neither ADB reachability nor SSH login grants Ternuxx management authorization. See [ADR-0014](architecture/decisions/ADR-0014-proot-adb-and-management-tcp.md) for implementation gates and management service requirements.

Planned CLI contract:

```text
ternuxx ssh status
ternuxx ssh status --provider native
ternuxx ssh status --provider proot
ternuxx ssh start --provider native
ternuxx ssh stop --provider proot
ternuxx ssh logs --provider native
ternuxx ssh boot enable --provider proot
ternuxx ssh boot disable --provider native
```

The host CLI can inspect both providers and manage a guest service only through the ownership-aware PRoot adapter. A CLI running inside Debian defaults to guest-local status/control. A PRoot agent may reach native SSH for an explicitly authorized bounded diagnostic/management operation; it must not gain arbitrary host shell access from connectivity alone. Any cross-provider control names its target explicitly, verifies authorization at the target boundary, applies a timeout, and returns a structured result. If PRoot is unavailable, native SSH and services remain operational and only the guest operation fails. If an unmanaged `sshd` already owns a port or process, report it and refuse takeover until the user selects an explicit adoption/migration flow.

GUI settings and service pages call the same validated service manager as the CLI. They must show provider, service state, bind address, port, authentication mode, boot state, logs, and the last operation result. Start/stop/boot enablement has the same preview and confirmation in both interfaces. GUI buttons never run raw shell text or silently change configuration. Changes made in CLI appear in GUI status and vice versa.

The default profile uses key authentication, denies root login, and binds loopback for local device access. A user can explicitly select LAN access after reviewing exposure and network binding; the manager must not enable a public listener by default. Host and guest keys are never copied or shared automatically. Do not put private keys, passwords, or pairing material in Ternuxx logs or backups. If OpenSSH is missing in a provider, keep local GUI/CLI control available and show the package preview for that provider without switching to the other SSH service.

## Shared workspace contract

The first bridge should be one clearly named Ternuxx workspace, not the whole Termux home. Commands name input/output paths below that root. A run record stores provider, argv as an array, working directory, environment allowlist, start time, exit result, and output paths. Secrets are not copied across by default. Users can add a deliberate mount later with a preview and read-only option.

## Continuity and resource ownership

Persistent checkpoints and reboot evidence are native-owned and stored in Ternuxx's private Termux storage. A checkpoint must be sufficient to inspect pending work after reboot without preserving an agent process. On reboot, native services recover and report first. Guest operations remain pending until a fresh PRoot session exists and the owner requests continuation. Cross-provider task records include source/target provider, operation ID, bounded request, authorization result, timeout/result status, and sanitized recovery details. They exclude secrets and unnecessary personal paths.

Native and guest process/resource ownership is separate. Stopping PRoot may stop only guest-owned processes and must leave independent native SSH/services healthy. Restarting native services must not mutate guest rootfs/session state. A Wake Lock is attributed to the specific active workload/service that acquired it; another provider or service cannot release it. These are requirements, not verified behavior; acceptance evidence is tracked in [ADR-0010](architecture/decisions/ADR-0010-native-termux-autonomy.md).

## Session and resource ownership

Ternuxx owns only the processes it starts through its adapter. The existing Ternux launcher remains untouched and is never called for cleanup. Because the inspected `~/x.sh` kills matching X11/VirGL/PulseAudio processes and removes wildcard sockets before starting, the new provider must start its own tracked session and reuse only the reviewed Debian command/environment contract. It must not falsely report that it is controlling a session started by `x.sh`.

The host owns the X11 server and optional host PulseAudio endpoint for a selected session. The guest gets only the display/audio values and mounts needed by that run. Guest D-Bus stays a guest session; host D-Bus is not mounted into Debian. A guest desktop session and native XFCE session cannot both claim the same display lifecycle.

PRoot does not provide the same PID, network, IPC, cgroup, or security isolation as a kernel container. The manager must describe this as a Linux userland/compatibility layer, not a sandbox boundary. It cannot promise that systemd works inside the guest.

## Delivery sequence

1. **Boot and lifecycle:** native, PRoot, and hybrid profiles; owner tracking; one display/service owner; safe logs and recovery journal.
2. **PRoot parity:** preserve the Ternux Debian rootfs and its exact verified graphics/session environment through a separate adapter; read-only discovery before any command.
3. **Useful bridges:** selected file handoff, native-to-guest argv-safe command dispatch, GUI app launch, audio/display integration, and result return.
4. **Workflow routing:** app catalog and installer show provider; Doctor and optimization report each provider; hybrid workflow rules explain where commands and data run.
5. **Capability proof:** run the same suitable workload in native and PRoot separately, record actual renderer/delegate, correctness, thermal/power state, and limitations. Do not infer parity from one successful layer.

Each step is gated on a read-only compatibility check first. Device-changing work, installing add-on APKs, changing Android permissions, and testing boot settings require explicit owner authorization. Until then, implementation stays within repository changes or disposable fixtures.


## Debian GUI modes managed by Ternuxx

The full PRoot XFCE desktop is launched with `tx pgui`. Auto mode selects independent Termux:X11 `:0` when the Native desktop is stopped and nested Xephyr `:2` when Native `:1` is running. Explicit `standalone` and `nested` modes enforce the same lifecycle ownership checks. Native PulseAudio stays on the authenticated loopback endpoint; Debian keeps its own Zink/Turnip glibc stack. The nested desktop is foreground-controlled with Ctrl-C, while standalone has `tx pgui status|stop`. Individual Debian shortcuts remain routed through `tx mng app launch` on Native `:1`. Current device evidence and display/GLX limitations are in [the PRoot GUI report](evidence/2026-10-20-proot-full-gui.md).
