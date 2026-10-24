# Historical PRoot GUI experiment on display :0

> **Historical record, superseded 2026-10-24.** Ternuxx is Native Termux-only. PRoot implementation and operations described below have been retired and must not be used as current setup instructions. Current behavior is documented in [the product vision](../PRODUCT-VISION.md), [phase status](../PHASE-STATUS.md), and [Native-only retirement audit](../evidence/2026-10-24-native-only-proot-removal-audit.md).

This page records the 2026-10-18 dual-app Android user 999 experiment. That cloned-Activity path was deferred after the owner reported that the PRoot desktop was not visible there. Do not use the old direct script examples below as the current launch interface.

For the current interactive full Debian XFCE route, use `tx pgui start`: with Native XFCE running on `:1`, it starts nested Xephyr `:2`; with Native XFCE stopped, it selects standalone `:0`. `tx pgui status` inspects state and `tx pgui stop` stops only a verified standalone session; close nested mode from its owning terminal. Individual Debian GUI applications can instead open on the Native desktop through the shared `tx mng app launch` route. The nested GLES context reported Zink/Turnip, but nested GLX/DRI3 draw and visible presentation remain unverified; see [2026-10-20 full PRoot GUI evidence](../evidence/2026-10-20-proot-full-gui.md) and [operations guidance](../OPERATIONS.md).

The 2026-10-18 standalone test used private supervisor state under `~/.local/share/ternuxx/proot-display0/` and isolated XFCE config, cache, data, and runtime paths in the guest. Its stop path signaled only the recorded supervisor and owned process groups. The test did not invoke `xgo`, `~/x.sh`, broad process cleanup, or PulseAudio cleanup. The old direct script examples are retained only as historical record; use the current `tx pgui` command contract above.

## Device check — 2026-10-18

The owner-authorized test started XFCE from Debian PRoot on `DISPLAY=:0` while the native desktop remained on `:1`. A PRoot `xdpyinfo -display :0` request succeeded, and `glxinfo -B` from the same PRoot/display reported `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`. The Android X11 clone was already open for user 999; native Termux could not start that cross-user activity itself. GUI process readiness was verified, but visual confirmation of the floating window was not captured.

After the check, `proot-gui0.sh stop` stopped its recorded `:0` process groups. ADB then showed no `:0` X server or XFCE process; native `:1` PID 28608 and the pre-existing agent PRoot PID 16526 were still present.


## Follow-up device check — 2026-10-18

A repeat run used the launcher's actual shared `/tmp` namespace. `proot-distro login debian --shared-tmp --user sbj -- env DISPLAY=:0 xdpyinfo` succeeded while the launcher-owned `termux-x11 :0` and `xfce4-session` processes were running. The owner reported that the PRoot GUI was not visible in the floating clone app, so Android clone rendering remains **not verified / failed from the user's observation**. The native shell cannot query Android user 999 packages or start its Activity because Android denies cross-user access.

The test session was stopped with `proot-gui0.sh stop`. Post-stop process inspection showed no test `:0` server or XFCE process; native `:1` (PID 28608) and the pre-existing agent PRoot (PID 16526) remained running. The current launcher starts its X server from native Android user 0 and assumes the Android user 999 clone Activity can display it; that assumption needs a supported cross-profile connection path before this can be called a working clone setup.


## Decision — 2026-10-18

The cloned Android user 999 path is deferred. The owner reported that the PRoot GUI did not appear in that floating clone Activity. The Android user 999 clone Activity path remains deferred and is not wired to the active shell aliases. Later work added explicit standalone `:0` and nested Xephyr `:2` launch modes through `tx pgui`; see [current GUI qualification evidence](../evidence/2026-10-20-proot-full-gui.md). That evidence records process/audio/GLES context checks but leaves nested GLX draw, visible presentation, and clean-guest reproduction unverified. Specific PRoot applications use the active Native display as documented in [PRoot GUI apps in the native desktop](../PROOT-SHARED-X11.md).
