# PRoot GPU renderer check — 2026-10-18

## Result

A read-only `glxinfo -B` process inside the existing Debian 13 PRoot selected the Adreno 825 through Zink/Turnip:

```text
DISPLAY=:1
Device: zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP)) (0x44030000)
Version: 25.0.7
Accelerated: yes
OpenGL renderer string: zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))
OpenGL core profile version string: 4.6 (Core Profile) Mesa 25.0.7-2+deb13u1
```

## Process context

- Host: Termux `u0_a490`; Android 16; Adreno 825 / SM8735.
- Guest: existing `debian` PRoot, Debian 13, user `sbj`.
- Display: active Termux:X11 `:1`, currently owned by Ternuxx native XFCE.
- Guest environment selected the existing Ternux Zink route: `MESA_LOADER_DRIVER_OVERRIDE=zink`, `GALLIUM_DRIVER=zink`, `TU_DEBUG=sysmem,noconform`, and `MESA_VK_WSI_DEBUG=sw`.
- `/dev/kgsl-3d0` was bound as guest `/dev/kgsl`; `/dev/dri` was bound into the guest.
- `MESA_SHADER_CACHE_DISABLE=true` was used for this diagnostic.
- The check ran `glxinfo -B`; it did not start/stop XFCE, invoke `~/x.sh`, install packages, or alter Ternux lifecycle state.

## What this proves and what remains

This confirms that a GL context created by the Debian PRoot process on the active `:1` X server used Zink backed by Turnip on Adreno 825, and Mesa reported `Accelerated: yes`. Native Termux's separate `llvmpipe` result is unchanged.

A short guest `glxgears` smoke workload also completed: `521 frames in 5.0 seconds = 104.076 FPS`. The program reported synchronization to vertical refresh, so this number is a display-limited smoke result, not a GPU performance benchmark. Together with the renderer output, it confirms a real GL draw loop ran through the selected Zink/Turnip path. No application-specific correctness or compute throughput was measured.

This did not test the existing Ternux-owned `:0` desktop because that desktop was not active; nor does it implement the Ternuxx PRoot provider. P4 remains open pending its ownership-aware provider, exact Ternux session reproduction, selected workload checks, and preservation gates.
