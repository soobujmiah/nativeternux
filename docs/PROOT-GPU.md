# Reusing Ternux's GPU-Accelerated PRoot

NativeTernux can reuse the existing Ternux Debian environment as an optional Linux workload provider. Based on the reviewed source and native-driver result, this is the currently documented GPU route for Linux workloads on the inspected Adreno 825 device. Live rendering still needs to be confirmed in the active guest session. It does not make the native Termux graphics stack GPU accelerated: graphics applications must run inside the Debian PRoot where Ternux configures Zink/Turnip.

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

- NativeTernux has not yet launched an application through Ternux's existing rootfs.
- NativeTernux has not independently rerun a live `glxinfo` renderer check in that desktop during this project review.
- A Zink shader-cache directory alone is not proof of the renderer used by a current process.
- Sharing the X11 display does not move a native Termux application's rendering into Debian. The application itself must run inside PRoot to use the guest Mesa/Turnip stack.

Treat these as separate evidence: project documentation/source is reviewed; device runtime behavior must be checked in the active session before reporting it as currently verified.

## Use the existing setup today

NativeTernux does not need to manage the current GPU desktop for you to use it:

1. If the Ternux Debian XFCE desktop is already running, open its Debian terminal and continue there. Do not restart it just for this check.
2. If no desktop is running and you intend to start one, use `ternux start` from native Termux and let Ternux own that session. Do not do this while another X11 desktop/session is active.
3. In the Debian terminal, run `glxinfo -B` to inspect the current OpenGL renderer. If it reports Zink backed by Turnip, run GPU workloads from that same terminal (for example, `blender` if installed in the guest).
4. End a session only through the Ternux workflow that started it.

Do not run `nativeternux start` alongside this session. NativeTernux's start command is currently only a readiness stub, and a future native desktop could contend for the same X11/audio services.

## Safe integration boundary

The current Ternux launcher owns the display, audio setup, and teardown. Its start path uses display `:0`, and its stop/launcher cleanup can terminate Termux:X11, PulseAudio, VirGL, and remove X11/audio socket paths. Therefore NativeTernux must not start or stop Ternux implicitly, run its cleanup, rewrite `~/x.sh`, reinstall packages, upgrade Debian, or create/remove/trim the `debian` rootfs.

Until an explicit adapter with ownership-aware lifecycle is implemented, use the existing Ternux command independently to start its desktop, then run the intended Linux workload within that Ternux Debian session. Do not start a second NativeTernux-owned Xfce session on the same display. Stop the session only through the owner that started it.

A future NativeTernux integration should be opt-in and read-only with respect to the rootfs by default. It should detect the configured distro/user/backend, check for a running session and display conflict, execute only explicitly requested guest commands, and never invoke broad Ternux stop/cleanup. Destructive package or rootfs operations require separate explicit commands and confirmation.

## Verification checklist

To verify the active renderer, open a terminal inside the existing Ternux Debian desktop and run these read-only commands:

```bash
command -v glxinfo
printf 'DISPLAY=%s\n' "$DISPLAY"
glxinfo -B | sed -n '/OpenGL vendor string/p; /OpenGL renderer string/p; /OpenGL version string/p'
```

Run GPU-dependent applications from that Debian desktop terminal after checking the renderer. Expected evidence is Zink backed by Turnip, not `llvmpipe`. If `glxinfo` is unavailable, do not install it as part of a NativeTernux check; mark live renderer verification pending until the owner chooses a suitable verification route.
