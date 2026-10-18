# Existing workstation preservation baseline

**Observed:** 2026-10-18 14:26 UTC. **Repository source:** `5232a20b63c5f9f66d8f3e74208ed5bff8c4340a`. **Route:** authenticated Native Termux development shell on port 8022. This is a dated snapshot; it does not qualify reboot behavior or claim that every feature was tested in this invocation.

## Preservation boundary and current identity

- The Debian guest was entered read-only with `proot-distro login debian --user sbj`. It reports Debian GNU/Linux 13 (trixie), `DEBIAN_VERSION_FULL=13.7`, user `sbj`, and an aarch64 PRoot-Distro kernel identity.
- The host-side container tree exists at `$PREFIX/var/lib/proot-distro/containers/debian/rootfs`. The login command and rootfs tree were observed; no rootfs path was copied, moved, or changed.
- `proot-distro ps` reported existing PID 16526, container `debian`, login user `sbj`, uptime about 4h27m. It was left running. No PRoot session was killed or closed.
- Guest package database contained 1511 entries. Selected installed packages include FFmpeg 7.1.5, Mesa utilities 9.0.0, Vulkan tools 1.4.304, and XFCE 4.20. The guest also has Mesa Vulkan/DRI, Vulkan loader, and OpenCL ICD loader packages in its package inventory. No package operation was run.

## Existing launcher contracts observed

- Native `~/.bashrc`: `db` runs `proot-distro login debian --shared-tmp --user sbj`; `droot` runs `proot-distro login debian --shared-tmp` (root user).
- `x` expands to `~/x.sh`; `xgo` expands to `bash ~/x.sh`. `~/x.sh` is a 112-byte executable wrapper to `$HOME/ternuxx/scripts/proot-x11-app.sh`.
- The wrapper starts one selected guest GUI application on the already running native Ternuxx X11 display; its script also requests the Termux:X11 Android activity. It does not run the existing Ternux full-desktop launcher. This inspection did not execute the wrapper.
- Ternux source docs describe its default `~/x.sh` as a GPU-configured desktop launcher and `killx` as its X11/audio helper. The owner clarified that the current Native `.bashrc` aliases and `~/x.sh` are intentionally customized for the active workflow. Treat this as an owner-customized installed entrypoint, not a defect to repair. Ternuxx must leave `x.sh`, `x`, `xgo`, and `killx` untouched and use an explicit app/session adapter when needed.
- Native Ternux reports `running`, `x11_running=yes`, `launcher=present`; Ternuxx reports `stopped` with no display/supervisor/XFCE. `ternux info --json` and `ternux backend show --json` report Adreno 825, Vulkan available, configured `zink`, and renderer unknown. A native `.X11-unix/X1` socket exists, but the process probe did not expose a matching owner; display/session ownership remains `UNVERIFIED`.

## Ternux repository configuration and live status

The local Ternux repository checkout was not present in either the Native Termux home or the Debian guest home. A read-only remote-ref check resolved `soobujmiah/ternux` `main` to `9fda63162426f77ee575b5f6729d8799a30f51b7`; source-derived facts below are pinned to that commit and are not treated as installed-state proof.

- Ternux documents Debian as the default/verified guest. Its Adreno route selects Zink → Vulkan → Turnip, exposes KGSL, and sets `MESA_LOADER_DRIVER_OVERRIDE=zink`, `GALLIUM_DRIVER=zink`, `TU_DEBUG=sysmem,noconform`, `MESA_VK_WSI_DEBUG=sw`, shader cache settings, and X11 shared-memory flags. VirGL is a separate `virpipe` route with a host renderer; installed backend selection is not proven by source defaults.
- Ternux documents a host PulseAudio bridge on `127.0.0.1:4713` and a Debian client endpoint. Current host `ternux status --json` reported `status=running`, `x11_running=yes`, `pulseaudio=stopped`, `virgl=stopped`, `launcher=present`; `ternuxx status --json` reported its own desktop `stopped` with display `none`. This is Ternux's status result, not proof of display visibility, guest session ownership, or audible playback.
- The source offers an optional prerelease CPU/Vulkan `llama.cpp` extension and a separate experimental SM8735/Hexagon HTP extension. The latter is explicitly not production-ready: current documented safe inference config uses HVX-only matmul with flash attention off; HMX/flash-attention configurations have correctness failures, and a clean-idle comparison found HTP slower than Vulkan. Source evidence for another Ternux repo's HTP experiment must not be presented as Ternuxx implementation or as proof it is installed here.
- Live host `ternux state --json` records `phase_extras` complete and `backend=zink`; host `ternux backend show --json` reports `backend=zink`, `vulkan=yes`, `available_backends=zink,virgl`, and `renderer=unknown`. This is configuration/capability reporting, not a live rendered/inference workload. `ternux extension list --json` returned `Unknown command: extension` in the installed v1.4.0 CLI, even though the newer pinned GitHub docs describe extension commands. The documented `$HOME/.local/opt/ternux-extensions` directory was absent in Debian; `llama-cli` and the documented HTP launcher were not found in the bounded PATH/target-path checks. The installer records `phase_extras` completion but does not identify selected optional extras in the status output. This does not rule out a custom location or model elsewhere. No model filenames or personal workspace contents were enumerated.
- Guest `getconf GNU_LIBC_VERSION` returned glibc 2.41. `/dev/kgsl-3d0` exists in the guest; `/dev/dri` could not be listed by user `sbj` (permission denied). The documented Mesa packages are held (`libegl-mesa0`, `libgbm1`, `libgl1-mesa-dri`, `libglx-mesa0`, `mesa-vulkan-drivers`), confirming package-hold protection is currently present. No package or permission change was made.

Pinned upstream references: [Ternux configuration](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/docs/CONFIGURATION.md), [Ternux installation and optional extensions](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/docs/INSTALLATION.md), [CPU/Vulkan llama.cpp guide](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/guides/llama-vulkan-extension.md), and [experimental HTP guide](https://github.com/soobujmiah/ternux/blob/9fda63162426f77ee575b5f6729d8799a30f51b7/guides/llama-htp-experimental.md).

## Runtime and acceleration inventory

| Capability | Current evidence | Status |
|---|---|---|
| Debian/XFCE userland | Debian 13.7, XFCE 4.20 packages, `xfce4-terminal` available in prior package inventory | `WORKING_WITH_LIMITATIONS`; package presence does not certify an active desktop |
| CPU inference | No llama/ollama executable was found in the checked PATH, and the documented Ternux extension directory was absent; matching package search found no such runtime | `UNKNOWN`; Ternux documents optional CPU/Vulkan llama.cpp, but its install state outside the checked standard extension directory and model paths were not exhaustively inventoried |
| Vulkan / graphics | Ternux host `backend show` reports configured `zink`, Vulkan `yes`, renderer `unknown`. Guest Mesa Vulkan drivers/loader/tools and ICD descriptors are installed; Adreno KGSL node exists. A separate dated `glxinfo -B` on `:1` selected Zink/Turnip and reported `Accelerated: yes`; see [renderer evidence](P4-proot-gpu-renderer-2026-10-18.md). | `CONFIGURED_NOT_VERIFIED` currently; historical `WORKING_WITH_LIMITATIONS` for the dated `:1` GL probe only |
| OpenCL | `ocl-icd-libopencl1` was present in the package inventory; no `/etc/OpenCL/vendors` entry was observed in the targeted read-only path check. | `CONFIGURED_NOT_VERIFIED` at best; no OpenCL device/runtime test was run |
| QNN / HTP / NPU | No matching package or executable was found in the bounded package/PATH search. | `EXPERIMENTAL` in the separate Ternux project for SM8735 only; the documented install path is absent here and live HTP execution is unverified |
| Current GUI/audio context | One-shot `ternux status --json` without `DISPLAY` reported display unset, X11 unreachable, and PulseAudio unreachable. This describes that probe context only. | Current desktop/audio ownership `UNVERIFIED` |

The renderer probe above is historical evidence and is not a reproducible benchmark or proof of the existing Ternux-owned `:0` desktop. Package or ICD files alone do not prove backend usability. Ternux documents optional Vulkan inference and an experimental HTP extension; this Ternuxx baseline does not adopt or claim either runtime. No inference, Vulkan, OpenCL, or graphical context was initialized during this inventory.

## Repository/documentation alignment

- Canonical project vision: `docs/PRODUCT-VISION.md`; technical provider boundary: `docs/ARCHITECTURE.md` and `docs/HYBRID-INTEGRATION.md`; detailed existing graphics evidence: `docs/PROOT-GPU.md` and linked P4 evidence.
- Human current state: `CURRENT_STATE.md`; phase state source: `project/phase-state.json`; generated phase view: `docs/PHASE-STATUS.md`; deterministic Git/CI state: `.repo/STATUS.md`; durable implementation instructions: `AI_ASSISTANT.md`.
- Existing Ternuxx PRoot scope is partial: installed-distro/status diagnostics, selected guest verification, app/shortcut management, and a GUI-app handoff exist. A general workload dispatcher and full PRoot lifecycle adapter are not implemented. CLI/service foundations exist; TUI, Web UI, and general Graphical UI are not complete. Do not infer four-interface parity from individual CLI, web foundation, or shortcut-management slices.
- Existing source maps product phases P0-P10 rather than the master directive's A-F overview. Keep the established P0-P10 state machine and map the A-F outcomes into those phases; do not create a competing phase-state format.

## Safety result and next gate

No files inside the Debian guest were written; no package, launcher, environment, process, desktop, audio service, or rootfs state was changed. The existing PRoot session PID 16526 remains untouched. Native repository worktree was clean at the starting commit. Next, finish the docs consistency reconciliation and then continue the serial P3/P4 gates: keep 8023 listener ownership `UNVERIFIED`, retain the separate lifecycle qualification plan, and implement an ownership-safe adapter only after its P3 prerequisites are resolved. Reboot remains `UNVERIFIED` without explicit owner-approved testing.


## Owner clarification and live recheck — 2026-10-18 14:40 UTC

The owner clarified that the active Native Termux GUI is the Ternux session and the customized `~/x.sh` wrapper is intentional. This is not stale launcher drift and must not be “fixed” by restoring Ternux's default script. Current read-only host checks: `ternux status --json` reports v1.4.0 running/X11 yes; `ternux backend show --json` reports Zink and Vulkan yes, renderer unknown. Debian PRoot `DISPLAY=:1 glxinfo -B` reports Vendor Mesa, Device `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, Mesa 25.0.7, Accelerated yes. This directly verifies the GLX test process on `:1`, not the owning X server PID or every XFCE process. `glxgears` FPS is not acceleration proof and is not a benchmark. The full single-app handoff result is in [Ternux session app handoff evidence](2026-10-18-ternux-session-app-handoff.md).
