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

## What is not established by this repository

- Ternuxx does not yet implement an ownership-aware provider for launching workloads through Ternux's existing rootfs. The one-off read-only `glxinfo -B` and `glxgears` checks below used the existing guest but did not exercise a Ternuxx-managed launch lifecycle.
- On 2026-10-18, Ternuxx independently ran `glxinfo -B` and a short `glxgears` draw loop inside Debian 13 PRoot on active display `:1`; the renderer was Zink backed by Turnip on Adreno 825 and reported `Accelerated: yes`. The five-second result was refresh-synchronized, not a performance benchmark. Ternuxx did not establish that this was the Ternux-owned `:0` desktop. See [P4 renderer evidence](evidence/P4-proot-gpu-renderer-2026-10-18.md).
- A Zink shader-cache directory alone is not proof of the renderer used by a current process.
- Sharing the X11 display does not move a native Termux application's rendering into Debian. The application itself must run inside PRoot to use the guest Mesa/Turnip stack.

Treat these as separate evidence: project documentation/source is reviewed; device runtime behavior must be checked in the active session before reporting it as currently verified.

## Use the existing setup today

Ternuxx does not need to manage the current GPU desktop for you to use it:

1. If the Ternux Debian XFCE desktop is already running, open its Debian terminal and continue there. Do not restart it just for this check.
2. If no desktop is running and you intend to start one, use `ternux start` from native Termux and let Ternux own that session. Do not do this while another X11 desktop/session is active.
3. In the Debian terminal, run `glxinfo -B` to inspect the current OpenGL renderer. If it reports Zink backed by Turnip, run GPU workloads from that same terminal (for example, `blender` if installed in the guest).
4. End a session only through the Ternux workflow that started it.

Do not run `ternuxx start` alongside an existing Ternux or Ternuxx desktop. The native Ternuxx lifecycle has been exercised on the recorded target and can own its own session, but it must not contend with Ternux's display/audio lifecycle. The `:1` PRoot renderer check is not evidence about the existing Ternux-owned `:0` session. Keep provider startup opt-in and owner-scoped.

## Safe integration boundary

The current Ternux launcher owns the display, audio setup, and teardown. Its start path uses display `:0`, and its stop/launcher cleanup can terminate Termux:X11, PulseAudio, VirGL, and remove X11/audio socket paths. Therefore Ternuxx must not start or stop Ternux implicitly, run its cleanup, rewrite `~/x.sh`, reinstall packages, upgrade Debian, or create/remove/trim the `debian` rootfs.

Until an explicit adapter with ownership-aware lifecycle is implemented, use the existing Ternux command independently to start its desktop, then run the intended Linux workload within that Ternux Debian session. Do not start a second Ternuxx-owned Xfce session on the same display. Stop the session only through the owner that started it.

A future Ternuxx integration should use a documented, ownership-aware Ternux workload interface with a narrow typed workload contract. It should detect the configured distro/user/backend, check for a running session and display conflict, and never invoke broad Ternux stop/cleanup. Until that interface and lifecycle contract are reviewed and verified, Ternuxx keeps guest execution limited to its bounded read-only version/status diagnostics. Destructive package or rootfs operations require separate explicit commands and confirmation.

## Verification checklist

To verify the active renderer, open a terminal inside the existing Ternux Debian desktop and run these read-only commands:

```bash
command -v glxinfo
printf 'DISPLAY=%s\n' "$DISPLAY"
glxinfo -B | sed -n '/OpenGL vendor string/p; /OpenGL renderer string/p; /OpenGL version string/p'
```

Run GPU-dependent applications from that Debian desktop terminal after checking the renderer. Expected evidence is Zink backed by Turnip, not `llvmpipe`. If `glxinfo` is unavailable, do not install it as part of a Ternuxx check; mark live renderer verification pending until the owner chooses a suitable verification route.
