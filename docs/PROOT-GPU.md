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

`--backend` is an expected renderer class for verification; it does not activate/switch a graphics backend. A VirGL request that observes Zink is a mismatch, not a VirGL test pass. `tx db` defaults to the already verified Zink/Turnip path. `tx db --backend virgl` asks the Native Ternuxx VirGL service to start or reuse its exact owned server, then sends `GALLIUM_DRIVER=virpipe` and the shared-TMP socket path to the existing Debian guest. The service is explicit and persistent because another guest process may be a client. `tx virgl stop` refuses when socket clients or ownership cannot be proven absent. Do not change an active guest session just to obtain a result.

The VirGL lifecycle implementation and CLI handoff pass isolated tests. Current Native `tx virgl status --display :1` reports stopped; no server was started in this qualification increment. A live PRoot renderer/workload and GUI visual check remain required before VirGL can be called qualified. The installed optional Native provider is `virglrenderer-android`; it is not added to the base install plan.

## Preserve existing configuration

Do not replace the Debian rootfs, remove packages, or edit guest profile hooks based on their names. The installed `proot-distro` login writer owns its generated profile. Ternuxx passes the required display, audio, and selected graphics values through explicit launch arguments and filters Android runtime variables. Before any guest configuration mutation, inventory active consumers and capture content, mode, owner, hash, and a scoped recovery copy. Preserve the active `tx db` session and current Native GUI/audio services during qualification.

PulseAudio uses Ternuxx's private managed configuration and authenticated cookie in the current path. The package `$PREFIX/etc/pulse/default.pa` is not the active configuration. Leave it unchanged unless a reproduced defect is causally tied to it and a rollback is verified.

See [PRoot session safety](architecture/PROOT-SESSIONS.md), [capability matrix](architecture/CAPABILITY-MATRIX.md), and the [current execution evidence](evidence/2026-10-20-workstation-qualification-execution.md).
