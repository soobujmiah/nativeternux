# Reusing Ternux's GPU-Accelerated PRoot

Ternuxx can reuse the existing Ternux Debian environment as an optional Linux workload provider. Based on the reviewed source and recorded guest probe, this is the currently documented GPU route for Linux workloads on the inspected Adreno 825 device. A live rendering check selected Zink/Turnip on display `:1`; the configured Ternux `:0` path did not pass the read-only X11/renderer handoff. A current process check saw the `:1` Termux:X11 process that Ternuxx verifies as its own while Ternux reported `running`/X11-present. The checked-out Ternux source uses process-presence status detection, but the installed script was not proven identical to that checkout. No active Ternux-owned `:0` desktop is established. It does not make the native Termux graphics stack GPU accelerated: graphics applications must run inside the Debian PRoot where Ternux configures Zink/Turnip.

## What is established

The existing Ternux project documents and implements this graphics path:

1. Termux starts Termux:X11 and PulseAudio.
2. `proot-distro login` enters the existing Debian rootfs with shared temporary storage.
3. `/dev/kgsl-3d0` is exposed in the guest as `/dev/kgsl`; `/dev/dri` is also bound.
4. The guest process receives `DISPLAY`, `MESA_LOADER_DRIVER_OVERRIDE=zink`, and `GALLIUM_DRIVER=zink`, plus Ternux's Turnip/Zink settings.
5. The guest starts XFCE with `dbus-launch --exit-with-session startxfce4`.

Ternux's current installation guide labels Zink/Turnip as the measured Adreno route and its manual says to verify the live renderer inside the desktop with `glxinfo | grep "renderer string"`. A Zink renderer containing `MESA_TURNIP` is the expected evidence; `llvmpipe` means software rendering. See the [Ternux installation guide](https://github.com/soobujmiah/ternux/blob/main/docs/INSTALLATION.md), [Ternux manual](https://github.com/soobujmiah/ternux/blob/main/docs/MANUAL.md), and [configuration reference](https://github.com/soobujmiah/ternux/blob/main/docs/CONFIGURATION.md).

The native Termux test recorded in [RESEARCH.md](RESEARCH.md) shows its packaged Turnip ICD rejecting Adreno 825. That result applies to the tested native package/process. It does not invalidate Ternux's separately provisioned Debian driver path.

## Existing Ternux inference extensions

The separate Ternux repository at the reviewed `9fda63162426f77ee575b5f6729d8799a30f51b7` revision documents an optional prerelease CPU/Vulkan `llama.cpp` extension and a distinct experimental SM8735/Hexagon HTP extension. The HTP guide limits its device evidence to that experiment: HVX-only matmul with flash attention disabled produced bounded known-answer results; HMX and flash-attention configurations have recorded correctness failures, and HTP was slower than Vulkan in one clean-idle comparison. It is not a supported production backend and has no automatic CPU/Vulkan fallback. See the [Ternux CPU/Vulkan extension guide](https://github.com/soobujmiah/ternux/blob/main/guides/llama-vulkan-extension.md) and [experimental HTP guide](https://github.com/soobujmiah/ternux/blob/main/guides/llama-htp-experimental.md).

These are Ternux-owned optional extensions, not Ternuxx implementations. In the 2026-10-18 read-only guest check, the documented extension root was absent and `llama-cli` was not in the checked PATH; custom install paths and model files were not exhaustively inventoried. Installed/runtime state therefore remains unknown. Reuse must discover and invoke an existing runtime through a typed adapter without reinstalling it, moving models, or changing its configuration.

## What is not established by this repository

- Ternuxx now has a narrow, opt-in `proot.app.launch` handoff to an already-running Ternux X11 session. It checks Ternux's self-reported running/X11 state, the Zink/Vulkan profile, an explicit display socket, and guest X11 connectivity; it does not own session lifecycle or dispatch arbitrary workloads. Ternuxx also has a bounded, headless probe profile and an opt-in foreground Debian login profile with exact-session ownership checks. These do not start or supervise a GUI, and the interactive profile has not been live-qualified. General background workload dispatch and GUI/session lifecycle remain unqualified.
- On 2026-10-18, both a pre-handoff renderer probe and the current app-handoff session probe ran `glxinfo -B` inside Debian 13 on `:1`; the renderer was Zink/Vulkan on Adreno 825 (`MESA_TURNIP`) and reported `Accelerated: yes`. The five-second `glxgears` result was refresh-synchronized, not a performance benchmark. Current evidence ties the guest client to the Native Termux Ternux-reported live session, but does not prove X11 server process ownership. See [P4 renderer evidence](evidence/P4-proot-gpu-renderer-2026-10-18.md) and [current session app-handoff evidence](evidence/2026-10-18-ternux-session-app-handoff.md).
- A Zink shader-cache directory alone is not proof of the renderer used by a current process.
- Sharing the X11 display does not move a native Termux application's rendering into Debian. The application itself must run inside PRoot to use the guest Mesa/Turnip stack.

Treat these as separate evidence: project documentation/source is reviewed; device runtime behavior must be checked in the active session before reporting it as currently verified.

## Use the existing setup today

Ternuxx does not need to manage the current GPU desktop for you to use it:

1. If the Ternux Debian XFCE desktop is already running, open its Debian terminal and continue there. Do not restart it just for this check.
2. If no desktop is running and you intend to start one, use the established Ternux workflow and let Ternux own that session. Do not do this while another X11 desktop/session is active.
3. In the Debian terminal, run `glxinfo -B` to inspect the current OpenGL renderer. If it reports Zink backed by Turnip, run GPU workloads from that same terminal (for example, `blender` if installed in the guest).
4. End a session only through the Ternux workflow that started it.

Do not run `ternuxx start` alongside an existing Ternux or Ternuxx desktop. The native Ternuxx lifecycle has been exercised on the recorded target and can own its own session, but it must not contend with Ternux's display/audio lifecycle. The `:1` PRoot renderer check is not evidence about the existing Ternux-owned `:0` session. Keep provider startup opt-in and owner-scoped.

## Safe integration boundary

The current Ternux launcher owns the display, audio setup, and teardown. Its start path uses display `:0`, and its stop/launcher cleanup can terminate Termux:X11, PulseAudio, VirGL, and remove X11/audio socket paths. Therefore Ternuxx must not start or stop Ternux implicitly, run its cleanup, rewrite `~/x.sh`, reinstall packages, upgrade Debian, or create/remove/trim the `debian` rootfs.

The narrow app-handoff adapter can target Ternux only after its desktop is already running and the user explicitly supplies the display. Ternuxx never starts, stops, or cleans up the Ternux session. Do not start a second Ternuxx-owned Xfce session on the same display. Stop the session only through the owner that started it.

A future Ternuxx integration should use a documented, ownership-aware Ternux workload interface with a narrow typed workload contract. It should detect the configured distro/user/backend, check for a running session and display conflict, and never invoke broad Ternux stop/cleanup. The current Ternuxx-owned profiles are fixed and typed; they do not dispatch arbitrary workload commands or claim lifecycle control of a Ternux-created desktop. See the PRoot session architecture at architecture/PROOT-SESSIONS.md. Destructive package or rootfs operations require separate explicit commands and confirmation.

## Verification checklist

To verify the active renderer, open a terminal inside the existing Ternux Debian desktop and run these read-only commands:

```bash
command -v glxinfo
printf 'DISPLAY=%s\n' "$DISPLAY"
glxinfo -B | sed -n '/OpenGL vendor string/p; /OpenGL renderer string/p; /OpenGL version string/p'
```

Run GPU-dependent applications from that Debian desktop terminal after checking the renderer. Expected evidence is Zink backed by Turnip, not `llvmpipe`. If `glxinfo` is unavailable, do not install it as part of a Ternuxx check; mark live renderer verification pending until the owner chooses a suitable verification route.


## Earlier same-day read-only qualification — superseded

On Native Termux, `DISPLAY=:1 ./tx proot verify --distro debian --guest-user-from ternux-state --display :1 --backend zink` completed after the isolated verifier passed the private Native PulseAudio cookie as one explicit file bind. Debian reported X11 reachable, guest PulseAudio reachable, and `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`. The command reported no guest writes, package changes, or service start/stop. The guest owner remains unverified. The historical `--guest-user-from ternux-state` account source has since been removed; current verification uses an explicit guest user or the unique regular account discovered directly from the installed Debian rootfs. This verifies the Zink/Turnip renderer for this bounded Debian process on `:1`; it does not prove native Termux rendering or arbitrary workloads. Native GUI diagnostics separately report llvmpipe and unsupported Vulkan for the installed Native route. VirGL remains in the documented/configurable provider set but was stopped in the included Ternux status snapshot; NPU remains unverified. See the [current execution evidence](evidence/2026-10-20-workstation-qualification-execution.md).


## Superseding Native-owned handoff check (2026-10-20)

The current Ternuxx verifier no longer calls the Ternux guest companion or reads Ternux state. It resolves the unique regular Debian account from the installed rootfs and runs a fixed read-only glxinfo/pactl probe. On this device, Debian PRoot :1 previously reported Zink/Vulkan with Adreno 825 MESA_TURNIP; current source now explicitly passes DISPLAY, the Native authenticated audio cookie, and KGSL/DRI handoff for Ternuxx-managed sessions. Source fixtures pass; repeat live renderer/audio checks before treating the new launcher path as qualified. The earlier Ternux companion record remains historical. VirGL remains preserved but inactive in the observed snapshot; NPU remains experimental/unverified.


## Superseding direct Ternuxx verification — 2026-10-20

On Native Termux, `tx proot verify --distro debian --guest-user-from rootfs --display :1 --backend zink` exited 0: X11 reachable, renderer `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, and authenticated Native PulseAudio reachable. A real `tx db -- sh -c ...` command confirmed the guest did not receive the proot-distro Android ART/classpath/storage variables and retained only the explicit `DISPLAY=:1`, Native PulseAudio server/cookie, and Zink/Turnip handoff. `glxinfo -B` reported `Accelerated: yes`; `pactl` identified the Native OpenSL_ES_sink. The existing interactive PRoot session and Native :1 desktop remained running. This is renderer/protocol evidence for the tested Debian process, not proof for all workloads or visible/audio output. Native GTK startup separately logged `VK_ERROR_INCOMPATIBLE_DRIVER`; NPU remains unverified. See the current [workstation execution evidence](evidence/2026-10-20-workstation-qualification-execution.md).
