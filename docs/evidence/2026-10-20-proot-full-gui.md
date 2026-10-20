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
- Native XFCE now has a separate **PRoot Apps** category, generated from visible Debian GUI desktop entries and routed through the shared management service.

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
- A separate `es2_info` on `:2` created an OpenGL ES 3.2 context on Mesa 25.0.7-2+deb13u1 with renderer `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`. This verifies renderer selection for that GLES context only.
- In this repeat check, guest `glxinfo -B` on `:2` failed with `couldn't find RGB GLX visual or fbconfig`. `vulkaninfo --summary` listed Adreno 825 / Mesa Turnip and llvmpipe devices but repeatedly reported no DRI3 presentation support and an invalid/missing `XDG_RUNTIME_DIR`. The nested Xephyr log emitted repeated `DRI3 not available`; `es2gears_x11` did not produce an observable window or benchmark result. The visible nested desktop and GPU draw/presentation remain unverified, so full nested GPU acceleration is **partial/unqualified** despite the GLES context's Turnip renderer string.
- The same active Native `:1` Debian OpenGL verifier returned `renderer_class=zink_turnip`, X11/audio reachable. This is separate from nested `:2` and does not establish nested GLX.
- Ctrl-C in the owning terminal closed the nested desktop. Follow-up confirmed the `:2` socket absent, Native `:1` running, Native PulseAudio running, guest `:1` verifier still complete, and pre-existing Debian PRoot PID 25612 still alive.

### Xephyr launch-mode comparison — 2026-10-20

- Compared the committed `-glamor_gles2` launch with two bounded experiments: `-glamor` and no explicit glamor flag. Each used the Ternuxx-managed nested wrapper while Native XFCE `:1` stayed live.
- Both alternatives produced the same device result: DRI3 extension unavailable, GLX draw failed with zero frames, and a Zink/Turnip GLES 3.2 context without a verified draw. Repeated `DRI3 not available` messages remained.
- Neither alternative improves or qualifies nested GPU rendering. Restored the tracked launcher to `-glamor_gles2`; the worktree has no launcher change. Both test sessions were closed from their owning terminals and the `:2` socket is absent.
- No package was installed and no existing Debian user configuration or service was changed. Normal Ternuxx startup initialized only its isolated private XFCE XDG overlay.

## Native PRoot Apps shortcut repair — 2026-10-20

- Root cause: pre-existing Native XFCE generated launchers called `tx app -- PROGRAM`, while the source CLI did not register `app`; this caused menu clicks to fail before reaching the shared app service.
- Implemented a typed desktop-entry-ID launch through `proot.app.launch`, automatic discovery from the installed guest's visible `/usr/share/applications/*.desktop` records, and the separate **PRoot Apps** category. The native desktop supervisor refreshes it at startup; `tx mng papps sync` refreshes it after guest package changes. The overlay merges the parent XFCE menu, excludes PRoot launchers from Accessories, and leaves conflicting user-owned files untouched.
- Live sync discovered and generated 35 launchers from the current Debian rootfs; the session logout command was excluded. The menu XML parsed, and all generated desktop files passed `desktop-file-validate` after adding a standard `Utility` category alongside the custom category.
- `gtk-launch ternuxx-proot-app-thunar` and `tx mng app launch --desktop-id thunar.desktop --display :1` both started Thunar; `xdotool` observed a visible `sbj - Thunar` window. The GUI menu was not clicked by the agent; owner visual confirmation of the category is still outstanding.
- The running Native :1 desktop, authenticated PulseAudio, and pre-existing PRoot shell PID 25612 remained available after nested test cleanup.

## Final verification and access note — 2026-10-20

- The full Native Termux suite passed 577/577 in 107.628 seconds earlier in this session. After final small launch-path/security hardening, the focused shortcut, authorization, and management-session suite passed 31/31 in the mounted project workspace.
- A later full suite run from the Debian PRoot workspace ran 577 tests and returned 7 failures plus 2 errors, clustered in Native desktop process-identity/lifecycle and Android VirGL process fixtures. This PRoot-hosted run is not a Native Termux qualification; its platform-sensitive failures are preserved rather than represented as a product regression or a pass.
- After that run, loopback SSH connections from the PRoot workspace to development ports 8022 and 8023 completed the SSH banner/authentication exchange but failed with `Bad packet length` before a command could return. No Termux, SSH, Native GUI, or managed service was restarted or changed to recover the channel. The final device-side rerun of the full suite could not be made through those endpoints.
- `git diff --check`, shell syntax checks, Python compilation, phase-doc refresh, and repository knowledge verification passed; repository knowledge verification reported zero findings.

## Implementation defects found during live bring-up

The first standalone attempts exposed and corrected argument-order, wrapper invocation, and login-shell display inheritance errors. No unrelated process was killed. For each failed startup, only the exact newly recorded PIDs were checked absent and `:0` socket/lock absence was verified before the generated private session record was reconciled. The final standalone and nested sessions passed the checks above.

### Repeat qualification after Debian D-Bus isolation

- Repeated standalone startup after adding the in-guest D-Bus adapter: tx pgui start --mode standalone reached identity-verified running state on :0; tx proot verify --distro debian --guest-user sbj --display :0 --backend zink returned status=complete, with X11 and authenticated Native audio reachable and renderer zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)).
- Attempted Native tx start --display 1 while standalone PRoot was active. It refused with exit code 1 and left PRoot running. After tx pgui stop, Native :1 started and the same Debian verifier returned complete on :1.
- Repeated nested start after D-Bus isolation: Xephyr :2 became ready and es2_info reported OpenGL ES 3.2, Mesa 25.0.7-2+deb13u1, renderer zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)). Ctrl-C/SIGINT to the exact foreground nested wrapper ran cleanup; :2 socket disappeared. Native :1, authenticated Native audio, and the pre-existing Debian PRoot shell (PID 25612) remained active.
- In nested mode, startxfce4 notes that an X server is already running on :2; DRI3, DPMS, and system integration warnings remain. GLES context creation and a Zink/Turnip renderer string are confirmed; an actual nested GPU draw/presentation is not. GLX/DRI3, audible playback, and visible Android-window confirmation remain unverified.
- scripts/repo_test.sh ran on Native Termux after the CLI, state-inspector compatibility fix, and test updates: 572 tests ran in 97.692 seconds; all passed (OK).

## Limitations

- These results qualify one device/runtime, the current Debian rootfs and its installed Xephyr/desktop stack. They do not establish compatibility across devices or freshly created guests.
- `xserver-xephyr` is declared in `config/proot/debian-trixie.json`, but no Ternuxx guest package installer/replay exists yet.
- Nested GLES context creation reports Zink/Turnip, but nested GLX and DRI3 are unavailable; hardware draw/presentation, visible UI, and audible output remain unverified.
- General PRoot TTY attach/detach/session ownership remains governed by the active P3 gate; this dedicated GUI supervisor does not qualify arbitrary PRoot sessions.
- Native and PRoot GUIs may not claim the standalone `:0` lifecycle at the same time. To use a full PRoot desktop while Native GUI is active, use nested mode; to use standalone, stop the managed Native GUI first.

## Evidence

Phase: `P3`
Phase: `P4`

- **P3 progress:** The dedicated GUI lifecycle test demonstrates a bounded, identity-checked Debian X11 workload, renderer verification, authenticated audio, and cleanup while preserving Native `:1` and the pre-existing PRoot shell. It does not resolve the separate general interactive TTY cwd/UID ownership gate, so P3 remains in progress.
- **P4 preparation:** The existing Debian XFCE now has separate Ternuxx standalone and nested launch routes, with a versioned package requirement for Xephyr and on-device Zink/Turnip/audio evidence. Fresh guest package/config replay and full provider parity remain unimplemented, so P4 remains planned.
## Native generic-menu cleanup — 2026-10-20

After the generated PRoot Apps menu was installed, the Native Termux shared XDG application directory still contained three obsolete Ternuxx launchers (`ternuxx-proot-files.desktop`, `ternuxx-proot-terminal.desktop`, and `ternuxx-proot-shortcut-manager.desktop`). The first two pointed to the old direct wrapper route and were superseded by discovered Debian desktop-ID launchers; the shortcut-manager item was also part of the old generic menu. Removed only these three files after checking their complete contents against the expected Ternuxx-generated entries. The generic directory now has no `ternuxx-proot-*.desktop` entries. The private Native XFCE `PRoot Apps` category and its 35 generated guest-app launchers remain in place. No unrelated or user-owned desktop entries were changed.
## Native XFCE generic-menu duplicate follow-up — 2026-10-20

The owner still saw many PRoot entries in generic Accessibility/Accessories menus. The active Native XFCE session was confirmed to use the private XDG paths under `$HOME/.local/share/ternuxx/xfce`. All 35 generated entries had `Categories=Utility;X-Ternuxx-PRoot;`; the standard `Utility` category could place them in XFCE's generic Accessories menu despite the overlay exclusion. The generator now assigns only `X-Ternuxx-PRoot`, and explicitly excludes that category from generic Accessories and Accessibility menus while including it in **PRoot Apps**. A live sync rewrote all 35 launchers, with zero category mismatches or user-file conflicts. The managed panel was restarted to refresh its menu cache; the Native `:1` XFCE session and Termux:X11 server remained running. Menu file/category state is verified; the owner should confirm the visible menu after refresh.
