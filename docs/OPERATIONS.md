# Doctor, management, and recovery

This document defines how NativeTernux should inspect and manage the workstation after installation. These are product requirements; commands that are marked planned are not implemented yet. The current CLI reports its real limits in `nativeternux help`.

## Operating principles

- A doctor run is read-only. It reports evidence, severity, likely cause, and a suggested next action. It never installs packages, changes Android permissions, edits another project's files, kills processes, or repairs state by itself.
- Every managed process, display, socket, package transaction, profile, and backup has an explicit owner and recorded identity. A matching process name alone is not proof that NativeTernux owns it.
- Mutating commands preview their target and impact before asking for explicit consent. An interrupted operation leaves a journal entry that can be inspected and resumed or rolled back through a purpose-built recovery action.
- Recovery works only on NativeTernux-owned data. It must refuse ambiguous targets and preserve the original Ternux Debian PRoot, its launcher, its process tree, and user data.
- Backups are local by default, integrity checked, versioned, and stored with restrictive permissions. Secrets such as tokens, private keys, and Android app data are excluded unless the owner explicitly chooses a documented, secure backup path.

## Doctor

`nativeternux doctor` should provide a concise overall state and detailed sections for host, packages, desktop/display, audio, storage, providers, acceleration, and recovery. `--json` returns stable machine-readable codes and fields; human output explains them without requiring the user to interpret raw shell errors.

Each finding has an ID, severity (`pass`, `info`, `warning`, or `error`), scope, observed value, timestamp/source, and a safe suggested action. Diagnostics distinguish unavailable, unverified, and failed. A GPU device node or installed driver is not reported as a working renderer; provider checks identify whether the result came from native Termux or the existing Debian PRoot. Doctor does not test by launching a desktop or workload unless a future command explicitly says it will do so and asks first.

Suggested actions link to the matching guide or an explicit command. A future `doctor --repair` may only offer a per-finding preview and must request confirmation for each state-changing repair; it is never an automatic fix-all switch.

## Server and session management

The management layer inventories NativeTernux-owned services and desktop sessions, plus read-only observations of external sessions. Initial managed services may include the Termux:X11 server, D-Bus session, PulseAudio only when NativeTernux started it, XFCE, and later an explicitly selected PRoot provider. A service record includes PID, process start time, executable identity, parent/session information, display, state directory, and the launch command version needed to reject stale PID reuse.

Planned commands include `status`, `service list`, `service inspect NAME`, and lifecycle actions such as `start`, `stop`, `restart`, and `reload` only where the service supports them. Each action names its provider and target. Stop and restart operate only on validated NativeTernux-owned identities. External or uncertain processes are shown as conflicts with a manual next step; they are never killed to make a command succeed.

The manager serializes operations that share a display or audio endpoint, reports lock ownership, detects stale operation journals, and gives a useful conflict message. It must not assume that Termux:X11's app window closing means the server process exited. Recovery from a lost client or orphaned process is a separate, explicit action after ownership is proven.

## Independent SSH services

Native Termux `sshd` and Debian PRoot `sshd` are independent services with their own identity, configuration, user/keys, logs, listener, and boot setting. NativeTernux presents the same service manager through CLI and GUI; state or actions from one interface are visible in the other. Commands name `--provider native` or `--provider proot` for mutations. From inside PRoot, the CLI defaults to guest-local control; host-side control stays with the Termux manager.

Since both providers share Android's network namespace, they require different ports and conflict checks. Default to loopback and public-key authentication; LAN exposure is an explicit, reviewed choice. Existing SSH services are detected read-only and are never stopped or adopted by matching process name alone. Missing OpenSSH disables only that provider's remote access, not the workstation UI or local CLI.

## Termux:Boot and Termux:API

These integrations are optional host capabilities, not requirements for the base desktop.

- **Termux:Boot:** provide owner-controlled `native`, `proot`, and `hybrid` profiles, plus CLI-only service profiles. Before enabling a profile, show the exact generated script, commands, display, wake-lock behavior, foreground/UI steps, and disable path. Never silently add or change files in `~/.termux/boot/`.
- **Native profile:** start NativeTernux-owned Termux:X11, required host services, and native XFCE; request the Termux:X11 Android activity. Track server, session, and visible GUI readiness separately.
- **PRoot profile:** start the existing Debian guest with the documented Ternux Zink/Turnip environment through a NativeTernux-owned, ownership-aware adapter. Do not call `~/x.sh` as the boot entry: the inspected launcher kills any matching Termux:X11/VirGL/PulseAudio processes and removes wildcard X11/audio sockets before it starts. That cleanup can disrupt the native profile or other sessions. Never edit `~/x.sh`; implement a separate adapter that starts and stops only processes it recorded itself.
- **Hybrid profile:** start one NativeTernux-owned X11 server and one native XFCE desktop, then make the existing Debian PRoot available for selected workloads on that display. Do not start a second XFCE session against the same display. A full PRoot desktop can be selected as the alternative `proot` profile or later assigned a separately validated display.
- **GUI visibility:** when Android allows the X11 activity to appear, report it as open; if it blocks or backgrounds the request, report “desktop services running; open Termux:X11 to view” and leave a user-action route. Do not report GUI-ready merely because `am start` returned success.
- **Scope of control:** CLI commands can manage the Termux-side services NativeTernux owns. They cannot override Android's activity/background policy, force the screen on/unlock the device, bypass app permissions, or guarantee that the OEM will keep a background process alive. Provide `boot status`, `boot profile`, `boot enable`, and `boot disable` flows with preview and explicit confirmation. The owner installs and opens the matching Termux:Boot app once and handles Android battery/background settings.
- **Boot safety:** boot scripts must be idempotent, log to NativeTernux-owned state, avoid duplicate sessions after reboot/retry, and only manage a PRoot session that the selected NativeTernux adapter started. The guest remains the existing Ternux Debian rootfs; do not run package operations, trim it, or alter its launcher. Any first-run/session configuration writes inside the guest must be listed in preview and require opt-in.
- **Termux:API:** expose only useful, individually selectable integrations such as share/receive a user-selected file, clipboard, notifications, battery/device status, and media controls when the matching API command exists. Check for both the Termux package and companion app at runtime. Calls that require Android permissions must explain and let Android's permission flow handle consent. API failure must leave core CLI and desktop workflows usable.
- **Background service management:** prefer Termux's supported service tooling when present, and record whether NativeTernux or an external service manager owns a process. Do not duplicate a service already managed by another owner. Wake locks are explicit, visible, and released through a matching user action; they are never enabled globally as a hidden performance setting.
- **Version and signing:** Termux add-on apps need a compatible signing source with the main Termux app. Doctor should report missing/mismatched companion capability without attempting to uninstall or replace apps.

Official references: [Termux:Boot](https://github.com/termux/termux-boot) and [Termux:API](https://github.com/termux/termux-api).

## Optimization controls

`optimize status`, workload profiles, storage analysis, and profile restore are planned under [Workload optimization](OPTIMIZATION.md). The optimizer is inspect-first. It changes only declared, per-job application settings after preview and consent; automatic thermal response is opt-in and can only reduce the selected workload. System governors, GPU clocks, thermal protections, and unrelated services remain outside its control.

## Dependency and APK fallback rules

The manager checks each profile's dependencies before enabling or starting it and reports the exact missing item. Fallback stays within the same capability boundary; it never silently changes provider or renderer.

| Missing capability | Safe fallback |
|---|---|
| Termux:Boot APK absent, disabled, or not initialized | Boot automation is unavailable. Keep manual `nativeternux start`/CLI controls available and show the official add-on setup guide; do not pretend boot is enabled. |
| `termux-services`/runit package absent | A Termux:Boot script may perform one-shot startup for selected owned services. Mark watchdog/restart supervision unavailable; do not silently install a manager. |
| Termux:X11 APK or companion package unavailable | CLI services may still start, but report no visible desktop and show the specific setup route. Do not report GUI-ready. |
| Native desktop packages unavailable | Keep CLI-only mode available; show a preview for the native package profile. Do not silently switch to the PRoot desktop. |
| Existing Debian PRoot or GPU path unavailable | Use native profile if its own prerequisites pass, otherwise CLI-only. Never silently fall back from hardware rendering to software or alter the guest. |
| Shizuku APK/server/watchdog unavailable | Continue with unprivileged Termux and PRoot features. Any ADB Wi-Fi setting control remains unavailable and requires a user action through Android settings or Shizuku's own app. |
| Termux:API companion or a particular API command unavailable | Hide/disable only that integration; keep the rest of the workstation usable. |

An APK being installed is not sufficient proof that its service, permission, signature compatibility, or requested capability is ready. Doctor reports app presence, companion command, permission/provider state, and live service readiness separately.

## Optional wireless ADB and Shizuku provider

Wireless ADB is separate from starting the workstation. NativeTernux desktop boot does not need Shizuku. A lower-dependency setup uses Termux:Boot to start selected Termux user services and, if installed, Termux's runit-based `termux-services` to supervise/restart those processes. This cannot grant Android shell identity or turn on protected ADB settings.

An advanced, separately enabled Shizuku provider may expose ADB-shell-level actions when the owner has installed/configured Shizuku and granted the required capability. The owner's ADT field notes describe a particular custom Shizuku build with a boot receiver, WorkManager start flow, and foreground watchdog. This is device-specific evidence for that build/version; it is not a feature guaranteed by upstream Shizuku. Upstream Shizuku documentation says non-root mode must be started again with ADB after each reboot. NativeTernux must detect and report the actual provider instead of assuming that Shizuku or its watchdog is present.

Before supporting any automatic ADB-over-Wi-Fi action, distinguish Android's paired Wireless debugging transport from a fixed `adbd` TCP port such as 5555. Do not infer one is active from a setting/property or open port alone. Report transport, listener, pairing/authorization, and Shizuku bridge as separate facts. Enabling a listener can expose a powerful shell interface on the local network; it must be off by default, show its bind/port and security impact, require explicit consent, and provide an immediate disable action. Never scan LAN ports, store pairing codes/ADB keys, or disable debugging that the user enabled outside NativeTernux.

The watchdog is owned by the Shizuku provider, not NativeTernux. NativeTernux may inspect provider health and show logs/status if available, but must not install a custom Shizuku APK, grant `WRITE_SECURE_SETTINGS`, change Android debugging settings, or keep restarting a failed provider without an explicit owner-approved operation. A restart loop needs a bounded retry count, backoff, and a visible failure state.

Official references: [Shizuku API requirements](https://github.com/RikkaApps/Shizuku-API#requirements), [Shizuku setup guide](https://shizuku.rikka.app/guide/setup/), and [Termux services](https://github.com/termux/termux-services).

## Recovery

Recovery has four distinct jobs:

1. **Operation journal:** record the planned operation, exact owned targets, completed steps, and rollback actions before the first mutation. On startup, show interrupted operations instead of silently replaying them.
2. **Configuration backup:** create a timestamped archive of NativeTernux configuration, manifests, and state metadata. Include schema and software version, checksums, and a clear list of included/excluded paths. Do not package rootfs images, shared storage, or secrets by default.
3. **Previewed restore:** `backup list`, `backup inspect`, and `restore --preview BACKUP` show archive integrity, version compatibility, files that would be added/replaced, and conflicts. Restore requires a separate explicit confirmation and writes only to NativeTernux-owned paths. Preserve the current state as a rollback snapshot before replacement.
4. **Repair and rollback:** support operation-specific compensation, such as removing a partially created NativeTernux state directory or restoring a known-good NativeTernux configuration snapshot. Never run generic `rm -rf`, package autoremove, rootfs pruning, or broad process cleanup as recovery.

A recovery command should fail closed when checksums fail, ownership cannot be established, the archive schema is newer or unknown, or a path resolves outside the NativeTernux state root. It should emit a recovery report with the chosen backup, affected paths, result, and any manual steps left.

Planned interface:

```text
nativeternux recovery status
nativeternux backup create [--name NAME]
nativeternux backup list
nativeternux backup inspect BACKUP
nativeternux restore --preview BACKUP
nativeternux restore BACKUP --yes
nativeternux recovery inspect OPERATION_ID
nativeternux recovery resume OPERATION_ID --yes
nativeternux recovery rollback OPERATION_ID --yes
```

The exact command names may change with CLI design. Preview and confirmation semantics, ownership checks, and the read-only default are required.

## Optional software catalog and website

The project website should be a maintained catalog and guide, not a remote shell installer. Each entry identifies the software, official publisher/project page, official package or download page, supported execution layer (Termux, existing Ternux PRoot, or both), architecture/runtime constraints, display/audio requirements, verification date, and known limitations. Installation links point to upstream documentation or let the local CLI create a verified package preview. The website must not ask visitors to paste an opaque `curl | sh` command.

Catalog entries are optional and cannot silently expand the base install. Package availability and links expire; a release workflow must re-check them against official sources before labeling an entry supported. Multiple distributions and display systems are compatibility candidates, not blanket guarantees. Termux:X11 is the initial display target; VNC or Wayland can be advertised only after a separate compatibility gate and evidence for the exact provider/device combination.

## Acceptance gates

- Doctor output is read-only, useful without root, stable in JSON, and distinguishes NativeTernux from external/Ternux-owned state.
- Manager status is accurate when processes exit unexpectedly, PIDs are reused, or another desktop is active. Conflicts fail closed.
- Native, PRoot, hybrid, and CLI-only boot profiles are separately selectable, idempotent, observable, and can be disabled from the CLI. A blocked Android activity is reported as a fallback state, never as a successful visible desktop. PRoot profile does not call the current broad-cleanup `~/x.sh`, and hybrid never starts a second XFCE on the same display.
- Every mutation has a preview, exact ownership boundary, explicit consent, journal, and documented rollback or recovery result.
- Backup/restore preserves permissions and metadata needed by NativeTernux, rejects path traversal and corrupt archives, and never modifies Ternux or shared user data.
- Catalog links resolve to official publishers, each listing has a review date and compatibility scope, and the CLI remains the trusted local installation path.
