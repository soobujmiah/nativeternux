# Native and PRoot end-to-end integration

I want Native Termux and my existing Debian PRoot to behave like two parts of one workstation from boot through workload completion. They keep separate package managers, runtime libraries, configuration, and ownership; NativeTernux connects them through explicit, narrow interfaces.

## End-to-end flow

```text
Termux:Boot
   │ selected profile: native / proot / hybrid
   ▼
NativeTernux host manager ── Doctor, logs, operation journal, recovery
   ├── Termux:X11 + one selected desktop session
   ├── Termux services: D-Bus/audio/optional runit services
   ├── Native apps + Termux:API actions
   └── Existing Debian PRoot provider
          ├── existing Ternux GPU environment and Linux apps
          └── selected workspace + argument-safe workload requests
```

The boot profile selects the desktop owner:

| Profile | Desktop owner | PRoot use | Display policy |
|---|---|---|---|
| `native` | Native XFCE in Termux | Available for selected guest workloads | One native XFCE session on the managed X11 display |
| `proot` | Existing Debian XFCE session | Full existing Ternux desktop/workload route | Guest desktop on the managed X11 display, using the reviewed Ternux environment |
| `hybrid` | Native XFCE in Termux | Guest applications and jobs on demand | One desktop session; do not launch a second XFCE against the same display |

`proot` and `hybrid` are separate boot choices. Starting both full desktop sessions simultaneously requires an independently validated second display and explicit resource/ownership handling.

## Integration matrix

| Boundary | Host-to-guest path | Guest-to-host return path | Rule |
|---|---|---|---|
| Boot and services | Termux:Boot selects the profile; NativeTernux starts owned host services and invokes the PRoot provider with an explicit profile | Status, logs, exit code, and journal state return to the host manager | Native, PRoot, and hybrid are independently startable/stoppable. Never run the current broad-cleanup `~/x.sh` as a boot command. |
| SSH access | Native Termux `sshd` and Debian PRoot `sshd` have separate service identities, configs, host keys, authorized-key files, ports, and boot settings | Each endpoint reports its own listener, auth mode, clients (when safely observable), logs, and lifecycle state | Same Android network namespace: reserve distinct ports and report bind address. Default loopback; LAN access is explicit opt-in. CLI and GUI use one shared manager. |
| Commands and apps | Native CLI selects a provider and passes argv, work directory, and an allowlisted environment to a guest command | Streamed output, result files, exit status, and signal status return to the caller | No shell-string concatenation or arbitrary guest-to-host shell execution. |
| Files | Bind only a NativeTernux workspace or a user-selected input/output path | Guest outputs land in the selected workspace; Termux:API can share a chosen file | No blanket `/sdcard`, Termux home, SSH key, or `.config` access. Bind read-only for inputs where practical. |
| Display | Native clients and guest GUI apps connect to the selected Termux:X11 display | Display readiness and GUI visibility are reported independently | A single XFCE owner per display. Guest X11 clients use the host display socket through the supported shared-tmp/X11 mechanism. |
| Audio | Native Termux owns PulseAudio when it starts it; guest clients receive the configured endpoint | Playback errors and process state return to Doctor/logs | One service owner. Stop only a service NativeTernux started and recorded. |
| Android APIs | Native Termux calls supported Termux:API commands after user action/permission | Result is returned to native CLI/UI; a selected result can be handed to PRoot | Do not expose API app credentials or arbitrary Android broadcasts inside the guest. |
| GPU/NPU | Native and guest workloads choose their own verified runtime/backend | Each result records provider, renderer/delegate, and workload proof | The Ternux Zink/Turnip route stays a guest process route; it does not become native GPU support. NPU remains unclaimed until proven per context. |
| Packages/catalog | Installer declares `termux` or `proot-debian` target and previews that package manager's exact transaction | Installed app metadata is recorded per provider | Never use apt to install across the host/guest boundary; optional app removal cannot prune the guest or base desktop. |
| Optimization | Select a profile and controls for the chosen provider/workload | Metrics, baseline comparison, thermal state, and restore status are reported | No silent cross-provider fallback, system clock changes, or thermal-protection bypass. |
| Doctor/recovery | Host manager gathers read-only findings from both environments | One report labels each finding's provider and owner | Repair/restore operates only within the explicitly selected NativeTernux-owned target. Existing Ternux state needs separate consent and backup. |

## Independent SSH services and controls

The Termux host SSH service and Debian guest SSH service are separate providers. The host service runs as the Termux app user; the guest service runs as the selected Debian PRoot user. They have separate configuration, host identity keys, authorized client keys, logs, boot enablement, and tracked process identity. The same SSH client may reach both endpoints, but each endpoint has its own configured address and port. PRoot does not provide a separate network namespace, so a port conflict is global to both services.

Planned CLI contract:

```text
nativeternux ssh status
nativeternux ssh status --provider native
nativeternux ssh status --provider proot
nativeternux ssh start --provider native
nativeternux ssh stop --provider proot
nativeternux ssh logs --provider native
nativeternux ssh boot enable --provider proot
nativeternux ssh boot disable --provider native
```

The host CLI can inspect both providers and manage a guest service only through the ownership-aware PRoot adapter. A CLI running inside Debian defaults to guest-local status/control and cannot silently change host services. Any cross-provider control names its target explicitly. If an unmanaged `sshd` already owns a port or process, report it and refuse takeover until the user selects an explicit adoption/migration flow.

GUI settings and service pages call the same validated service manager as the CLI. They must show provider, service state, bind address, port, authentication mode, boot state, logs, and the last operation result. Start/stop/boot enablement has the same preview and confirmation in both interfaces. GUI buttons never run raw shell text or silently change configuration. Changes made in CLI appear in GUI status and vice versa.

The default profile uses key authentication, denies root login, and binds loopback for local device access. A user can explicitly select LAN access after reviewing exposure and network binding; the manager must not enable a public listener by default. Host and guest keys are never copied or shared automatically. Do not put private keys, passwords, or pairing material in NativeTernux logs or backups. If OpenSSH is missing in a provider, keep local GUI/CLI control available and show the package preview for that provider without switching to the other SSH service.

## Shared workspace contract

The first bridge should be one clearly named NativeTernux workspace, not the whole Termux home. Commands name input/output paths below that root. A run record stores provider, argv as an array, working directory, environment allowlist, start time, exit result, and output paths. Secrets are not copied across by default. Users can add a deliberate mount later with a preview and read-only option.

## Session and resource ownership

NativeTernux owns only the processes it starts through its adapter. The existing Ternux launcher remains untouched and is never called for cleanup. Because the inspected `~/x.sh` kills matching X11/VirGL/PulseAudio processes and removes wildcard sockets before starting, the new provider must start its own tracked session and reuse only the reviewed Debian command/environment contract. It must not falsely report that it is controlling a session started by `x.sh`.

The host owns the X11 server and optional host PulseAudio endpoint for a selected session. The guest gets only the display/audio values and mounts needed by that run. Guest D-Bus stays a guest session; host D-Bus is not mounted into Debian. A guest desktop session and native XFCE session cannot both claim the same display lifecycle.

PRoot does not provide the same PID, network, IPC, cgroup, or security isolation as a kernel container. The manager must describe this as a Linux userland/compatibility layer, not a sandbox boundary. It cannot promise that systemd works inside the guest.

## Delivery sequence

1. **Boot and lifecycle:** native, PRoot, and hybrid profiles; owner tracking; one display/service owner; safe logs and recovery journal.
2. **PRoot parity:** preserve the Ternux Debian rootfs and its exact verified graphics/session environment through a separate adapter; read-only discovery before any command.
3. **Useful bridges:** selected file handoff, native-to-guest argv-safe command dispatch, GUI app launch, audio/display integration, and result return.
4. **Workflow routing:** app catalog and installer show provider; Doctor and optimization report each provider; hybrid workflow rules explain where commands and data run.
5. **Capability proof:** run the same suitable workload in native and PRoot separately, record actual renderer/delegate, correctness, thermal/power state, and limitations. Do not infer parity from one successful layer.

Each step is gated on a read-only compatibility check first. Device-changing work, installing add-on APKs, changing Android permissions, and testing boot settings require explicit owner authorization. Until then, implementation stays within repository changes or disposable fixtures.
