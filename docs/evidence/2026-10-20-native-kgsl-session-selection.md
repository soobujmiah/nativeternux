# Persistent Native KGSL session selection — 2026-10-20

## Implementation

Added `tx graphics native status|enable --prefix PATH|disable`. Enable checks that the supplied absolute prefix contains the extracted KGSL DRI driver, the Mesa Gallium library, and the GLVND EGL vendor manifest, then saves the prefix with mode 0600 in the private Ternuxx state directory. Future Native desktop starts apply `LD_LIBRARY_PATH`, `LIBGL_DRIVERS_PATH`, `MESA_LOADER_DRIVER_OVERRIDE=kgsl`, the EGL vendor manifest, `GLX_VENDOR_LIBRARY_NAME=mesa`, and disabled shader cache. Disable removes only this setting and returns future sessions to stock system Mesa. Fresh installs remain unchanged by default.

The candidate stays extracted in this checkout under `.qualification/native-mesa-0219ff84/`; no Mesa package or shared Termux library was installed or replaced. The selector is intentionally local/experimental.

## Live application

Enabled the validated prefix at `.qualification/native-mesa-0219ff84/extracted/data/data/com.termux/files/usr`. Restarted the exact Ternuxx-owned display `:1` through `./tx restart --display 1`. On a second restart using only the saved setting, the lifecycle log reported `Applying the saved Native KGSL graphics candidate to this desktop session.` The XFCE process environment contained the candidate `LD_LIBRARY_PATH`, DRI path, and `MESA_LOADER_DRIVER_OVERRIDE=kgsl`.

With the selected candidate environment, `DISPLAY=:1 glxinfo -B` exited 0 and reported Freedreno / Adreno 825, Mesa 26.3.0-devel commit `98f3d6229d`, and `Accelerated: yes`. `./tx gui status --json` reports `running`, display `:1`, supervisor/X11/XFCE `live`, and `gui_visible=unknown`. Native PulseAudio remained managed independently.

## Limits

This confirms the saved setting survives a Ternuxx desktop restart and the Native GLX renderer uses the candidate. It does not verify visible GUI output, other applications, display-presented FPS, Vulkan, inference, long-duration thermal stability, cold boot, or release readiness. The candidate is a local draft build; provenance/license review remains open. Disable with `./tx graphics native disable`, then restart to use stock Mesa again.

## Checks performed

- `bash -n lib/desktop.sh bin/tx lib/help.sh` passed.
- `./tx graphics native status`, enable, and status completed successfully.
- Two lifecycle restarts completed; the second used the persisted setting.
- Live process environment and `glxinfo -B` renderer were inspected.
- No repository test suite was run in this continuation.


## Follow-up: candidate path moved to private state

The locally qualified package tree was copied to `$TERNUXX_STATE_DIR/graphics/providers/native-mesa-0219ff84/`; the selected prefix and ICD manifest now use this private-state location instead of a checkout-relative path. Binary hashes matched during the copy. Existing running session was left untouched and still inherits its prior path; future starts use the private-state selection. The candidate artifact is not supplied or downloaded by a fresh installer.
