# Ternuxx Native Host and Debian PRoot Graphics

> **Historical record, superseded 2026-10-24.** Ternuxx is Native Termux-only. PRoot implementation and operations described below have been retired and must not be used as current setup instructions. Current behavior is documented in [the product vision](../PRODUCT-VISION.md), [phase status](../PHASE-STATUS.md), and [Native-only retirement audit](../evidence/2026-10-24-native-only-proot-removal-audit.md).

Ternuxx is the independent final workstation project. Native Termux is the host authority for display, audio, hardware discovery, and management. The existing Debian PRoot is the Linux workload environment and keeps its own glibc-compatible Mesa stack. The separate Ternux project is historical/reference context only; normal Ternuxx CLI, guest verification, and handoff do not require its CLI or state.

## Current verified path

The current Native display is `:1`. A read-only Ternuxx guest verification on Debian `:1` reports X11 reachable, authenticated Native PulseAudio reachable, and `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`. This verifies the selected renderer for that PRoot process/display. It does not claim all applications or inference workloads use the GPU.

Historical Native stock-Mesa checks reported OpenGL `llvmpipe` and Vulkan `VK_ERROR_INCOMPATIBLE_DRIVER`. Later bounded checks in a managed session using the locally staged KGSL/Freedreno candidate reported Adreno 825 with `Accelerated: yes` and rendered GL workloads. The latest Native `:1` status again reports Adreno 825 / accelerated, and bounded OpenGL verification rendered successfully. Do not apply either Native result to the Debian guest, or the guest renderer result to Native GTK.

The existing division is intentional:

- Native Termux owns Termux:X11 and the private, authenticated PulseAudio endpoint.
- Debian PRoot receives explicit display/audio settings and the existing kernel GPU device handoff.
- Debian uses ABI-compatible glibc Mesa/Turnip libraries from its own userspace. Do not copy Native Bionic libraries into Debian.
- Ternuxx owns its CLI, status, and service lifecycle; the separate Ternux CLI/state is not a runtime dependency.
- CPU remains the execution baseline. No Ternuxx inference runtime/model integration is currently implemented.
- Zink/Turnip remains the default Debian PRoot route. On 2026-10-22, the opt-in Native VirGL service and receipt-bound replay handoff rendered a real GLX workload through the installed tx entrypoint. The :1 server remains running because exact client ownership could not be established for stop; nested Xephyr :2 remains unqualified. VirGL does not replace or install the guest Mesa stack.
- NPU remains experimental and unverified. Visible vendor libraries alone do not establish device access or execution.

## Bounded guest verification

From Native Termux:

```bash
cd "$HOME/ternuxx"
DISPLAY=:1 ./tx proot verify --distro debian --guest-user-from rootfs \
  --display :1 --backend zink --json
```

A complete result should report `renderer_class=zink_turnip`, X11 reachable, and audio reachable. The probe payload does not install packages or control services. Entering the guest through installed PRoot-Distro 5.9.0 can nevertheless rewrite its generated `/etc/profile.d/termux-profile.sh` even with `--isolated`. This is a launcher side effect, so the whole command must not be treated as a filesystem-read-only operation. Current JSON now reports whole-operation `read_only=false` once guest login is attempted, identifies `probe_payload_read_only=true` and discloses `safety.launcher_profile_write_possible`. Both verification operations require `graphics.manage` plus CSRF over HTTP; read-only API access cannot launch them. Debian graphics status now reads inventory without entering the guest. A29 of the [active audit](../audit/REPOSITORY-AUDIT.md) still tracks exact probe preview/rollback. Preserve the working guest and use the separate qualification target for new lifecycle tests.

tx db defaults to the already verified Zink/Turnip path. tx db --backend virgl asks the Native Ternuxx VirGL service to start or reuse its exact owned server, then applies LIBGL_ALWAYS_SOFTWARE=true, GALLIUM_DRIVER=virpipe, and the display-specific shared-TMP socket path only to the launched guest process. The service is explicit and persistent because another guest process may be a client. Ternuxx keeps proot-distro's shared login profile on the stable Zink default; backend-specific values are applied after the login profile to the selected process, so a VirGL login cannot make parallel/future Zink shells inherit virpipe. tx virgl stop refuses when socket clients or ownership cannot be proven absent. Do not change an active guest session just to obtain a result.

A receipt-verified replay alias can use the same tx db --distro ternuxx-replay-* --backend virgl route without persisting graphics variables in that guest's profile. On 2026-10-22 the isolated replay guest rendered VirGL through the installed tx entrypoint and the bounded verifier. The server remained running because Android lsof could not map socket clients and fuser could not read /proc/net/unix; tx virgl stop correctly refused. See [the P4 VirGL route and cleanup recheck](../evidence/2026-10-22-p4-virgl-route-recheck.md).

The VirGL lifecycle implementation and CLI handoff pass isolated tests. Installed Native proot-distro 5.9.0 source confirms --shared-tmp binds Native TMPDIR to guest /tmp, matching the Ternuxx socket path. At the 2026-10-20 checkpoint, Native virglrenderer-android 1.3.0-1 started on :1 and status matched the Ternuxx-owned process/socket, but no PRoot VirGL client/workload had yet been launched. That live renderer/workload gate was completed on 2026-10-22 for the isolated replay guest; exact stop remains blocked because Android lsof returned no socket PID and fuser could not read /proc/net/unix. See [the current route and cleanup evidence](../evidence/2026-10-22-p4-virgl-route-recheck.md). The optional provider is not added to the base install plan.

## Preserve existing configuration

Do not replace the Debian rootfs or remove packages as a shortcut. The installed `proot-distro` login writer owns its generated profile, so do not edit that hook based on its filename alone. This does not impose a blanket ban on the owner-authorized Ternuxx guest adaptation: inspect the exact file, writer, and active consumers; preview the exact diff and effects; capture content, mode, owner, hash, and a scoped recovery copy; then apply only the reviewed Ternuxx operation and verify both the result and rollback. Prefer a Ternuxx-owned overlay when a package login writer would overwrite a direct edit. Preserve the active `tx db` session and current Native GUI/audio services during qualification.

PulseAudio uses Ternuxx's private managed configuration and authenticated cookie in the current path. The package `$PREFIX/etc/pulse/default.pa` is not the active configuration. Leave it unchanged unless a reproduced defect is causally tied to it and a rollback is verified.

See [PRoot session safety](../architecture/PROOT-SESSIONS.md), [capability matrix](../architecture/CAPABILITY-MATRIX.md), and the [current execution evidence](../evidence/2026-10-20-workstation-qualification-execution.md).


## Full Debian desktop through Ternuxx

Run `tx pgui` from Native Termux. If Native XFCE is running on `:1`, auto mode opens a nested Debian desktop on Xephyr `:2`; Ctrl-C in that terminal closes only the nested session. If Native GUI is stopped, auto mode starts a tracked standalone Termux:X11 desktop on `:0`. `tx pgui start --mode standalone|nested` selects a route explicitly, while `tx pgui status` and `tx pgui stop` manage the standalone session. Standalone `:0` cannot overlap the Native desktop. Both routes preserve Debian's glibc Zink/Turnip driver, and the authenticated Native PulseAudio server remains shared and Native-owned.

Live device evidence: an updated fixed probe on Native display `:1` rendered 486 bounded `glxgears` frames with the workload renderer `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`; it reports a verified GLX draw. The separate GLES context does not claim a GLES draw. Standalone `:0` passed the read-only guest X11/audio/Zink-Turnip verifier. Nested Xephyr `:2` created an OpenGL ES 3.2 context whose renderer string reports `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, then ran XFCE until Ctrl-C. This does not establish a fully accelerated nested desktop: repeated `DRI3 not available` warnings appeared, guest GLX failed to find an RGB visual, and Vulkan could enumerate Turnip but lacked DRI3 presentation support. Nested GPU draw/presentation and visual confirmation remain unverified. See [full GUI evidence](../evidence/2026-10-20-proot-full-gui.md). The separate `ternuxx-replay-p4` setup completed and its account, 54 requested packages, installed inventory and pinned driver hash were checked. Selected working-guest file hashes and root identity were preserved; this is not a full rootfs snapshot comparison. Graphics workload, rollback and all-client acceptance remain open; `xserver-xephyr` is recorded in the Debian package profile.
