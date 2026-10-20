# Ternuxx full Debian GUI qualification — 2026-10-20

## Scope

Implemented and exercised the `tx pgui` route for the existing Native Termux Ternuxx checkout at `$HOME/ternuxx`. Native XFCE, the existing Debian rootfs, authenticated PulseAudio, and the pre-existing Debian PRoot shell were preserved except for the explicitly authorized stop/start of the Ternuxx-managed Native `:1` desktop needed to exercise standalone `:0`.

The legacy `/sdcard/xx.sh` was not run or changed. It is not the management entry point; it performs broad X11/VirGL/PulseAudio cleanup and starts unauthenticated services. Ternuxx now owns the supported launch and lifecycle route.

## Interface and behavior

- `tx pgui` / `tx pgui start`: auto-select nested mode on Native `:1`, otherwise standalone `:0`.
- `tx pgui start --mode standalone`: requires Native desktop stopped, starts an identity-recorded Ternuxx supervisor and Debian XFCE on `:0`.
- `tx pgui start --mode nested`: requires verified Native `:1`, runs Xephyr `:2` plus Debian XFCE in the foreground. Ctrl-C in the launching terminal closes this nested session.
- `tx pgui status`: reports Native state, identity-checked standalone state, and `:2` socket presence without claiming socket ownership.
- `tx pgui stop`: signals only the verified standalone supervisor. Nested mode is closed from its owning terminal.
- Native `tx start` refuses a live or unclear standalone `:0` session. Standalone PRoot startup refuses a running or unclear Native session. Nested mode holds the shared desktop lifecycle lock for its lifetime.
- Shared per-app Debian shortcuts on Native `:1` remain available through `tx mng app launch`.

The Debian PRoot continues to use its glibc Zink/Turnip stack with `DISPLAY` scoped to the selected route, KGSL/DRI device binds, and authenticated Native PulseAudio at `tcp:127.0.0.1:4713`. The PulseAudio service stays Native-owned. Private XFCE XDG config/cache/data/runtime paths are isolated under the Ternuxx state directory. The versioned Debian profile now records `xserver-xephyr` as a base GUI requirement; fresh Debian provisioning and package replay remain unimplemented.

## Device evidence

### Standalone `:0`

- With Native `:1` verified stopped, `tx pgui start --mode standalone` reported the Ternuxx-owned Debian XFCE session running on `:0`.
- `tx pgui status` classified the recorded supervisor, Termux:X11 process, Debian wrapper process, and display as running.
- `tx proot verify --distro debian --guest-user sbj --display :0 --backend zink` returned `status=complete`: X11 reachable, audio reachable, renderer `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`.
- Native PulseAudio status remained `running`, endpoint `tcp:127.0.0.1:4713`, authenticated identity `matched`.
- `tx pgui stop` stopped the exact verified standalone session. It did not stop Native audio or the pre-existing PRoot shell.

### Nested `:2` inside Native `:1`

- With Native `:1` restored and verified running, `tx pgui start --mode nested` started Xephyr `:2`, printed `GL_RENDERER: zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, and launched Debian XFCE.
- A separate `tx db --display :2 -- /usr/bin/env DISPLAY=:2 es2_info` created an OpenGL ES 3.2 context on Mesa 25.0.7-2+deb13u1 with the same Zink/Turnip renderer.
- The nested route emitted repeated `DRI3 not available`, missing DPMS, and benign D-Bus/systemd/colord/polkit/GVFS warnings. Nested GLX is not verified and previously failed to find an RGB GLX visual. The visible desktop was not independently inspected; CLI GUI visibility remains unknown.
- Ctrl-C in the owning terminal closed the nested desktop. Follow-up confirmed the `:2` socket absent, Native `:1` running, Native PulseAudio running, guest `:1` verifier still complete, and pre-existing Debian PRoot PID 25612 still alive.

## Implementation defects found during live bring-up

The first standalone attempts exposed and corrected argument-order, wrapper invocation, and login-shell display inheritance errors. No unrelated process was killed. For each failed startup, only the exact newly recorded PIDs were checked absent and `:0` socket/lock absence was verified before the generated private session record was reconciled. The final standalone and nested sessions passed the checks above.

### Repeat qualification after Debian D-Bus isolation

- Repeated standalone startup after adding the in-guest D-Bus adapter: tx pgui start --mode standalone reached identity-verified running state on :0; tx proot verify --distro debian --guest-user sbj --display :0 --backend zink returned status=complete, with X11 and authenticated Native audio reachable and renderer zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)).
- Attempted Native tx start --display 1 while standalone PRoot was active. It refused with exit code 1 and left PRoot running. After tx pgui stop, Native :1 started and the same Debian verifier returned complete on :1.
- Repeated nested start after D-Bus isolation: Xephyr :2 became ready and es2_info reported OpenGL ES 3.2, Mesa 25.0.7-2+deb13u1, renderer zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)). Ctrl-C/SIGINT to the exact foreground nested wrapper ran cleanup; :2 socket disappeared. Native :1, authenticated Native audio, and the pre-existing Debian PRoot shell (PID 25612) remained active.
- In nested mode, startxfce4 notes that an X server is already running on :2; DRI3, DPMS, and system integration warnings remain. GLES rendering is confirmed, but GLX, DRI3, audible playback, and visible Android-window confirmation are not.
- scripts/repo_test.sh ran on Native Termux after the CLI, state-inspector compatibility fix, and test updates: 572 tests ran in 97.692 seconds; all passed (OK).

## Limitations

- These results qualify one device/runtime, the current Debian rootfs and its installed Xephyr/desktop stack. They do not establish compatibility across devices or freshly created guests.
- `xserver-xephyr` is declared in `config/proot/debian-trixie.json`, but no Ternuxx guest package installer/replay exists yet.
- Nested GLES is verified; nested GLX, DRI3, visible UI confirmation, and audible output are not.
- General PRoot TTY attach/detach/session ownership remains governed by the active P3 gate; this dedicated GUI supervisor does not qualify arbitrary PRoot sessions.
- Native and PRoot GUIs may not claim the standalone `:0` lifecycle at the same time. To use a full PRoot desktop while Native GUI is active, use nested mode; to use standalone, stop the managed Native GUI first.

## Evidence

Phase: `P3`
Phase: `P4`

- **P3 progress:** The dedicated GUI lifecycle test demonstrates a bounded, identity-checked Debian X11 workload, renderer verification, authenticated audio, and cleanup while preserving Native `:1` and the pre-existing PRoot shell. It does not resolve the separate general interactive TTY cwd/UID ownership gate, so P3 remains in progress.
- **P4 preparation:** The existing Debian XFCE now has separate Ternuxx standalone and nested launch routes, with a versioned package requirement for Xephyr and on-device Zink/Turnip/audio evidence. Fresh guest package/config replay and full provider parity remain unimplemented, so P4 remains planned.
