# P4 Ternux source and capability baseline

Reviewed: 2026-10-18 (Bangladesh time)

## Source identity and evidence classes

- Read-only `git ls-remote` resolved `soobujmiah/ternux` `refs/heads/main` to `9fda63162426f77ee575b5f6729d8799a30f51b7` during this review. The checked-out Ternuxx repository was not changed by that lookup.
- Pinned source references: [`lib/phases.sh`](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/lib/phases.sh), [`docs/INSTALLATION.md`](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/docs/INSTALLATION.md), and [`docs/MANUAL.md`](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/docs/MANUAL.md).
- Source claims below come from this pinned upstream revision. Device claims are separately marked and refer only to the dated Ternuxx-side PRoot probe; no Ternux-owned desktop was started or queried in this review.

## Capability and ownership matrix

| Area | Source-backed Ternux behavior | Evidence status and Ternuxx integration constraint |
|---|---|---|
| Display/session owner | `~/x.sh` starts Termux:X11 on `:0`, waits for the X socket, and launches the guest XFCE session. `xgo` also opens the Termux:X11 activity before running the launcher. | Ternux owns its desktop lifecycle. Ternuxx must not start a competing XFCE session on the same display or claim Android activity visibility from a server-ready signal. |
| Host audio | The launcher starts PulseAudio and exposes its native protocol on loopback TCP port 4713; the guest receives `PULSE_SERVER=tcp:127.0.0.1:4713`. | This describes the configured route, not proof that the current guest workload can hear audio. Do not start, stop, or reconfigure PulseAudio as part of a PRoot handoff. |
| Guest entry | The Zink path invokes `proot-distro login` for the configured distro with shared temporary storage, binds `/dev/kgsl-3d0` as guest `/dev/kgsl` and binds `/dev/dri`, then selects the configured non-root guest user (default shown by the installer is `ternux`). | This is the existing Ternux launch contract. Current installed distro inventory alone does not verify the configured distro, user, or ownership. Do not assume an installed Debian entry is Ternux-managed. |
| Zink/Turnip environment | The launcher sets `DISPLAY=:0`, `MESA_LOADER_DRIVER_OVERRIDE=zink`, `GALLIUM_DRIVER=zink`, `TU_DEBUG=sysmem,noconform`, `MESA_VK_WSI_DEBUG=sw`, shader-cache controls, locale, and guest runtime paths before running XFCE. | Preserve the configured variables as a group when routing a guest workload. Do not silently replace the backend or report a renderer from a different process/display as proof. |
| VirGL route | The alternate backend starts `virgl_test_server_android` and launches Debian with `GALLIUM_DRIVER=virpipe` and `MESA_GL_VERSION_OVERRIDE=4.3COMPAT`. | VirGL is a distinct configured route, not a fallback Ternuxx may select without owner choice. The active installed backend was not inspected in this review. |
| Desktop command | The reviewed launcher waits until `xdpyinfo -display :0` succeeds, prepares guest runtime directories, then executes `dbus-launch --exit-with-session startxfce4`. | This setup has side effects in the guest (directories, D-Bus state, XFCE settings). It is outside a read-only probe and must remain Ternux-owned until an additive adapter is implemented and separately authorized. |
| Cleanup and risk | The generated launcher runs broad `pkill` commands against Termux:X11/VirGL/PulseAudio and removes wildcard X11/audio socket paths before startup and in its exit trap. | **Prohibited integration path:** Ternuxx must never invoke `~/x.sh`, `killx`, Ternux start/stop/restart, or Ternux cleanup. These could disrupt the native Ternuxx desktop and unrelated sessions. |
| Workloads | The upstream docs list optional development, network, media, Blender, and LLM software selections. | Selection in the installer is not evidence that any option is installed or works on this device. Workload parity needs an owner-selected workload and same-process guest evidence. |

## Current device evidence and limits

- On 2026-10-18, Ternuxx's recorded Debian 13 PRoot `glxinfo -B` probe on the active `:1` display selected Zink backed by Turnip on Adreno 825 and reported `Accelerated: yes`. A short `glxgears` loop was also recorded as a draw-path check, not as a benchmark. See [P4 renderer evidence](P4-proot-gpu-renderer-2026-10-18.md).
- That probe is not the Ternux-owned `:0` desktop and did not exercise an existing Ternux GUI workload, audio workload, or agent session. It does not prove that the installed Ternux configuration currently uses Zink rather than VirGL.
- The latest Ternuxx read-only inventory reports Debian installed, guest/session ownership unverified, and `guest_entered: false`. It does not identify the installed guest user, active backend, current Ternux display/audio owner, or launcher version.
- The upstream `main` ref may advance. Re-pin/review the source before implementing or qualifying an adapter; do not copy executable source or configuration from this record as a substitute for live profile discovery.

## Adapter requirements derived from the matrix

1. Discover the fixed installed distro, configured guest user/backend, display, and session owner without changing Ternux files or launching its lifecycle.
2. Refuse absent or ambiguous ownership and display/audio conflicts. Never call Ternux's broad-cleanup launcher or stop path.
3. Start only explicitly requested guest workloads, pass argv as separate arguments, use a bounded environment allowlist, and expose only an owner-selected workspace rather than mounting all of Termux HOME or shared storage.
4. Record the child process identity and lifecycle state before offering stop/recovery controls. A one-shot process that exits must preserve its real exit status and output.
5. Verify renderer from the same guest process/display used by a selected graphics workload. Report `llvmpipe` as software rendering and do not infer NPU access from this GPU path.

P4 remains unqualified: source review establishes the baseline, but the Ternuxx adapter, current live Ternux-profile discovery, selected guest workload, and same-context renderer/feature-parity checks remain outstanding. No package, desktop, service, boot profile, or Debian guest state changed for this review.

## Current upstream ref recheck

- Read-only `git ls-remote https://github.com/soobujmiah/ternux.git refs/heads/main` during the 2026-10-18 continuation returned `9fda63162426f77ee575b5f6729d8799a30f51b7`, matching the reviewed pin above. No upstream checkout or local Ternux path was read or modified.


## 2026-10-18 read-only guest handoff recheck

- Ternux `main` still resolves to `9fda63162426f77ee575b5f6729d8799a30f51b7`. The current guest companion is version 1.4.0 and offers `ternux --version` plus read-only `ternux status`; its help sends lifecycle commands back to the Termux host. The Ternuxx adapter calls only those two guest commands and does not call `ternux start/stop`, `~/x.sh`, or cleanup.
- The verified Ternuxx diagnostic command uses an explicit Debian guest/user/display/backend, `--shared-tmp`, the selected Zink device binds, the source-documented PulseAudio endpoint, and shader-cache disable. On the active `:1` display, X11 and Zink/Turnip renderer checks passed; the first audio probe was unavailable. A later repeatability window had 10/10 complete guest checks after five consecutive failures; a subsequent silent PCM stream was refused, then direct checks passed again. Native `ternux status` said PulseAudio was stopped even while `pactl info` and loopback checks succeeded. The [audio evidence](2026-10-18-p3-ternux-audio-repeatability.json) records the contradictory snapshots; bridge stability and audible output remain unverified.
- This is a diagnostic handoff only. Guest/profile ownership and the active Ternux `:0` desktop remain unknown; no desktop/workload launch or feature-parity claim is made. See [P3 guest handoff evidence](2026-10-18-p3-ternux-guest-handoff.json).


### Native host-status correlation addendum

- Ternuxx read-only verification now reports the native Ternux `--json status` fields separately from direct guest checks. Ternux v1.4.0 host status tests process-name presence for PulseAudio (`pgrep -x pulseaudio`), while guest status tests `pactl info`; they are separate measurements, not a contradiction in Ternuxx ownership. The exact source behavior is visible in the [pinned Ternux desktop status function](https://github.com/soobujiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/lib/desktop.sh#L611-L634). Keep owner unverified and prefer endpoint probes for audio capability. Live evidence: [P3 audio/status correlation](2026-10-18-p3-ternux-audio-repeatability.json). No upstream Ternux file was changed.

- Read-only `ternux --json backend show` reports configured backend/Vulkan plus its host renderer probe. On 2026-10-18 it returned configured `zink`, Vulkan yes, renderer unknown; the Ternuxx-selected Debian guest independently returned Zink/Turnip on `:1`. This is cross-layer backend consistency, not proof that the guest is Ternux-owned or that its user/distro matches the unseen Ternux profile. See [P3 status correlation](2026-10-18-p3-ternux-audio-repeatability.json).


## Native Ternux profile-discovery recheck — 2026-10-18

- Read-only `ternux --json state`, `status`, and `backend show` reported version 1.4.0, installation state OK, configured backend Zink, renderer unknown, Ternux status running, and X11 process present. Read-only `ternuxx proot status` reports Debian installed without entering the guest and keeps ownership unverified.
- The current public CLI fields still do not identify the active guest distro/user pair or display, and they do not establish that the Debian inventory is Ternux-managed. The host renderer remains unknown. No state directory contents were read or copied; only allowlisted CLI summaries were recorded. No lifecycle, service, package, or rootfs mutation occurred. See [profile-discovery evidence](2026-10-18-p4-ternux-profile-discovery-recheck.json).
- P4 stays unqualified pending a supported ownership/profile interface and same-context workload evidence; this recheck does not authorize a Ternuxx start/stop adapter.

- Follow-up read-only `ternux --json info` and `ternux --json profile show` at 01:41:46–01:41:47 UTC also returned device/backend summary (v1.4.0, Zink, host renderer unknown). Neither API exposes active guest distro/user/display or rootfs ownership. This is now included in [profile discovery evidence](2026-10-18-p4-ternux-profile-discovery-recheck.json); no Ternux or guest state was mutated.


## Configured user/display correlation (2026-10-18)

- The installed Ternux host state file is owner-matched, regular, and mode 0600. A selective read of its documented configuration keys showed the configured guest user matches the explicit guest-verifier user, with install profile `base` and backend `zink`; the literal user value is omitted from shared evidence. Ternux state reports `phase_debian` complete, and `proot-distro` lists Debian. The installed Ternux launcher source sets `DISPLAY=:0` for both Zink and VirGL.
- Using those same configured guest inputs, Ternuxx read-only `proot verify` on `:0` returned partial (X11/renderer unavailable, audio reachable); on `:1` it returned complete with X11/audio reachable and Zink/Turnip. Both X0/X1 socket nodes existed, but that alone proves no server connectivity. Native `xdpyinfo` is absent; no package was installed.
- This identifies the configured user/backend/display path, but `:0` failed the handoff test while `:1` succeeds in the Ternuxx desktop context. Ternux process status and source configuration do not prove which rootfs/session owns the live X server. No Ternux start/stop, display launch, package action, guest write, or service change occurred. See [profile-discovery and display comparison evidence](2026-10-18-p4-ternux-profile-discovery-recheck.json).

- Post-probe noninterference check at 01:46:47 UTC: native desktop remained running on `:1` (X11/XFCE session present; GUI visibility unknown); read-only PRoot inventory remained Debian installed, guest not entered, owner unverified. No package/service/lifecycle action occurred during the display comparison.


## Ternux status and visible X11 process correlation — 2026-10-18

- At 02:02 UTC, `ternux --json status` said `running` / `x11_running=yes`; its pinned status implementation uses `pgrep -f termux-x11`, a presence check. The Termux-visible `ps` sample found a `termux-x11` process on `:1`, and its transient PID matched the X11 PID that Ternuxx Doctor validated as its owned session root moments later. The current checked-out Ternux repository at `38a5217` uses a process-presence check for its status field; the installed live script was not proven byte-identical to that checkout. The literal PID and argv are not retained.
- No `:0` Termux:X11 process was observed in that process-table sample. This does not rule out hidden or differently named processes and does not prove rootfs ownership; the separate guest handoff still reports `:0` partial and `:1` complete. Therefore Ternux self-reported `running` is insufficient to claim that its configured desktop is active. See [P3 X11 presence correlation](2026-10-18-p3-ternux-x11-presence-correlation-0202.json).
- No Ternux lifecycle, package, service, boot, or guest-write action was performed.

## 2026-10-18 installed interface recheck

- Read-only native commands at 05:56 UTC report installed Ternux v1.4.0, configured backend Zink, Vulkan available, and host renderer unknown. The installed `ternux --help` exposes install/start/stop/restart, diagnostics, profile/backend/state, benchmark, logs, update and uninstall commands; it advertises no generic `exec`, `run`, or workload dispatch interface.
- This confirms the implementation boundary in ADR-0006: Ternuxx can continue bounded read-only status/renderer diagnostics, but there is no supported installed command for an ownership-aware guest workload handoff. Do not bypass this by invoking `proot-distro login` with arbitrary user commands.
- Evidence: [installed Ternux CLI interface recheck](2026-10-18-p4-installed-ternux-interface-recheck-0600.json). No Ternux command changed state, entered the guest, started/stopped a session, or accessed packages/network. P4 remains planned and unqualified pending the P3 ownership contract and owner review of ADR-0006.

### Installed CLI file identity recheck — 2026-10-18 06:36 UTC

- A bounded read-only native check resolved `ternux` to `bin/ternux` relative to Termux `$PREFIX`; it is a 3,739-byte regular file, mode 0755, SHA-256 `03dc25c67debde8195673f5f5594651f3e4fd4466cbcb61f57ac01b4e48c233a`, and has no `dpkg` owner.
- The native `$HOME/ternux` Git checkout is absent. Therefore the installed command's source identity and its binding to the separately observed v1.4.0 output remain unverified. This does not change the earlier CLI help finding: no generic workload dispatch was advertised.
- No CLI was executed for this identity check, and no state, guest, package, service, or desktop was changed. See [installed CLI identity evidence](2026-10-18-p4-installed-cli-identity-0636.json).
