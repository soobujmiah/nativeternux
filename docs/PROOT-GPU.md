# Ternuxx Native Host and Debian PRoot Graphics

Ternuxx is the independent final workstation project. Native Termux is the host authority for display, audio, hardware discovery, and management. The existing Debian PRoot is the Linux workload environment and keeps its own glibc-compatible Mesa stack. The separate Ternux project is historical/reference context only; normal Ternuxx CLI, guest verification, and handoff do not require its CLI or state.

## Current verified path

The current Native display is `:1`. A read-only Ternuxx guest verification on Debian `:1` reports X11 reachable, authenticated Native PulseAudio reachable, and `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`. This verifies the selected renderer for that PRoot process/display. It does not claim all applications or inference workloads use the GPU.

Native Termux's separate `DISPLAY=:1 tx doctor --graphics --json` check reported OpenGL `llvmpipe` and Vulkan `VK_ERROR_INCOMPATIBLE_DRIVER`. Do not apply this Native result to the Debian guest, or the guest renderer result to Native GTK.

The existing division is intentional:

- Native Termux owns Termux:X11 and the private, authenticated PulseAudio endpoint.
- Debian PRoot receives explicit display/audio settings and the existing kernel GPU device handoff.
- Debian uses ABI-compatible glibc Mesa/Turnip libraries from its own userspace. Do not copy Native Bionic libraries into Debian.
- Ternuxx owns its CLI, status, and service lifecycle; the separate Ternux CLI/state is not a runtime dependency.
- CPU remains the execution baseline. No Ternuxx inference runtime/model integration is currently implemented.
- Zink/Turnip is the current observed Debian PRoot GPU route. VirGL now has an opt-in Ternuxx Native service and `tx db --backend virgl` handoff; the live renderer has not been switched or qualified. VirGL does not replace or install the guest Mesa stack.
- NPU remains experimental and unverified. Visible vendor libraries alone do not establish device access or execution.

## Read-only verification

From Native Termux:

```bash
cd "$HOME/ternuxx"
DISPLAY=:1 ./tx proot verify --distro debian --guest-user-from rootfs \
  --display :1 --backend zink --json
```

A complete result should report `renderer_class=zink_turnip`, X11 reachable, and audio reachable. The command enters the existing guest only for fixed read-only probes and does not change packages, services, or rootfs files.

`--backend` is an expected renderer class for verification; it does not activate/switch a graphics backend. A VirGL request that observes Zink is a mismatch, not a VirGL test pass. `tx db` defaults to the already verified Zink/Turnip path. `tx db --backend virgl` asks the Native Ternuxx VirGL service to start or reuse its exact owned server, then applies `GALLIUM_DRIVER=virpipe` and the shared-TMP socket path only to the launched guest process. The service is explicit and persistent because another guest process may be a client. Ternuxx keeps proot-distro's shared login profile on the stable Zink default; backend-specific values are applied after the login profile to the selected process, so a VirGL login cannot make parallel/future Zink shells inherit virpipe. `tx virgl stop` refuses when socket clients or ownership cannot be proven absent. Do not change an active guest session just to obtain a result.

The VirGL lifecycle implementation and CLI handoff pass isolated tests. Installed Native `proot-distro` 5.9.0 source (`$PREFIX/lib/python3.14/site-packages/proot_distro/commands/login/proot_cmd.py`) confirms `--shared-tmp` binds `$PREFIX/tmp` to guest `/tmp` for the normal Debian login, matching the Ternuxx socket path. On 2026-10-20, Native `virglrenderer-android` 1.3.0-1 started successfully on `:1` and `tx virgl status` matched the Ternuxx-owned process and socket. This verifies source-level path mapping and server startup only. `tx virgl stop` refused with exit 1 because Android `lsof` returned no socket PID and `fuser` could not read `/proc/net/unix`; the server remains running fail-closed. No PRoot VirGL client/workload was launched. A live guest renderer/workload and GUI visual check remain required before VirGL can be called qualified. The optional provider is not added to the base install plan.

## Preserve existing configuration

Do not replace the Debian rootfs, remove packages, or edit guest profile hooks based on their names. The installed `proot-distro` login writer owns its generated profile. Ternuxx passes the required display, audio, and selected graphics values through explicit launch arguments and filters Android runtime variables. Before any guest configuration mutation, inventory active consumers and capture content, mode, owner, hash, and a scoped recovery copy. Preserve the active `tx db` session and current Native GUI/audio services during qualification.

PulseAudio uses Ternuxx's private managed configuration and authenticated cookie in the current path. The package `$PREFIX/etc/pulse/default.pa` is not the active configuration. Leave it unchanged unless a reproduced defect is causally tied to it and a rollback is verified.

See [PRoot session safety](architecture/PROOT-SESSIONS.md), [capability matrix](architecture/CAPABILITY-MATRIX.md), and the [current execution evidence](evidence/2026-10-20-workstation-qualification-execution.md).


## Full Debian desktop through Ternuxx

Run `tx pgui` from Native Termux. If Native XFCE is running on `:1`, auto mode opens a nested Debian desktop on Xephyr `:2`; Ctrl-C in that terminal closes only the nested session. If Native GUI is stopped, auto mode starts a tracked standalone Termux:X11 desktop on `:0`. `tx pgui start --mode standalone|nested` selects a route explicitly, while `tx pgui status` and `tx pgui stop` manage the standalone session. Standalone `:0` cannot overlap the Native desktop. Both routes preserve Debian's glibc Zink/Turnip driver, and the authenticated Native PulseAudio server remains shared and Native-owned.

Live device evidence: standalone `:0` passed the read-only guest X11/audio/Zink-Turnip verifier. Nested Xephyr `:2` created an OpenGL ES 3.2 context whose renderer string reports `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, then ran XFCE until Ctrl-C. This does not establish a fully accelerated nested desktop: repeated `DRI3 not available` warnings appeared, guest GLX failed to find an RGB visual, and Vulkan could enumerate Turnip but lacked DRI3 presentation support. Nested GPU draw/presentation and visual confirmation remain unverified. See [full GUI evidence](evidence/2026-10-20-proot-full-gui.md). Fresh Debian provisioning remains unavailable; `xserver-xephyr` is recorded in the versioned Debian package profile for a future explicit setup/replay workflow.
