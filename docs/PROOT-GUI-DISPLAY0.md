# Independent PRoot GUI session on display :0

Start the existing Debian PRoot XFCE session using the already-open Termux:X11 app for dual-app user 999. Native Termux cannot launch an activity across Android users, so open the clone before starting:

```sh
bash ~/ternuxx/scripts/proot-gui0.sh start
```

Inspect and stop it with:

```sh
bash ~/ternuxx/scripts/proot-gui0.sh status
bash ~/ternuxx/scripts/proot-gui0.sh stop
```

The session is supervised independently under `~/.local/share/ternuxx/proot-display0/`; its XFCE config, cache, data and runtime paths are isolated inside the guest. Stop signals only the recorded supervisor, which stops only its own X11 and PRoot process groups. It does not invoke `xgo`, `~/x.sh`, broad process cleanup or PulseAudio cleanup. It leaves the native `:1` session and the current agent PRoot session alone.

Display `:0` lock/socket recovery is allowed only when the lock PID is absent and the socket refuses a connection. Unknown or live ownership fails closed. Android activity visibility is separate from process readiness; confirm XFCE is visible in the floating Termux:X11 app. The Android user can be overridden with `--android-user ID`; no existing shell aliases are changed.

## Device check — 2026-10-18

The owner-authorized test started XFCE from Debian PRoot on `DISPLAY=:0` while the native desktop remained on `:1`. A PRoot `xdpyinfo -display :0` request succeeded, and `glxinfo -B` from the same PRoot/display reported `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`. The Android X11 clone was already open for user 999; native Termux could not start that cross-user activity itself. GUI process readiness was verified, but visual confirmation of the floating window was not captured.

After the check, `proot-gui0.sh stop` stopped its recorded `:0` process groups. ADB then showed no `:0` X server or XFCE process; native `:1` PID 28608 and the pre-existing agent PRoot PID 16526 were still present.


## Follow-up device check — 2026-10-18

A repeat run used the launcher's actual shared `/tmp` namespace. `proot-distro login debian --shared-tmp --user sbj -- env DISPLAY=:0 xdpyinfo` succeeded while the launcher-owned `termux-x11 :0` and `xfce4-session` processes were running. The owner reported that the PRoot GUI was not visible in the floating clone app, so Android clone rendering remains **not verified / failed from the user's observation**. The native shell cannot query Android user 999 packages or start its Activity because Android denies cross-user access.

The test session was stopped with `proot-gui0.sh stop`. Post-stop process inspection showed no test `:0` server or XFCE process; native `:1` (PID 28608) and the pre-existing agent PRoot (PID 16526) remained running. The current launcher starts its X server from native Android user 0 and assumes the Android user 999 clone Activity can display it; that assumption needs a supported cross-profile connection path before this can be called a working clone setup.


## Decision — 2026-10-18

The cloned Android user 999 path is deferred. The owner reported that the PRoot GUI did not appear in that floating clone Activity. The `:0` experiment remains historical evidence only and is not wired to the active shell aliases. Current work uses one native Termux:X11 app and routes PRoot GUI applications to the active native display; see [PRoot GUI apps in the native desktop](PROOT-SHARED-X11.md).
