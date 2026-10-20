# Native and Debian graphics live recheck — 2026-10-20

Phase: `P4`
Phase: `P6`

## Native Termux

On the live Adreno 825 device, `tx mng graphics verify native opengl :1` completed an off-screen glmark2 run with renderer `Adreno (TM) 825`, score 581, and `render_verified=true`. `tx mng graphics verify native gles :1` created an OpenGL ES 3.2 context with the selected KGSL candidate and renderer `Adreno (TM) 825`; the API explicitly reports context-only evidence and does not claim a draw. Vulkan enumerates the device, but no Vulkan draw was verified.

A safe deliberate failure used an isolated empty graphics state and the intentional invalid `GALLIUM_DRIVER=ternuxx-intentional-missing-driver` value. The OpenGL primary attempt exited 1; the verifier then rendered off-screen using `llvmpipe (LLVM 21.1.8, 128 bits)`, score 109, and returned `fallback-rendered`, `accelerated=false`. This verifies the manager's bounded OpenGL verification fallback on this device. It does not yet retry ordinary application launches or choose per-workload GPU/NPU backends. NPU runtime and clean-install driver reproduction remain unverified.

A plain `es2_info` invocation without the saved candidate context reported llvmpipe and DRI3/Zink initialization warnings. The managed GLES probe, which loads the exact selected candidate path, reported Adreno instead. An `es2gears_x11` window could not be observed under the tested X11 route; an actual GLES draw/presentation therefore remains unverified.

The owner reports that Debian XFCE's device information displayed the GPU on standalone `:0`, and that Native XFCE is visible on the Android screen. Earlier live verification in [the full GUI evidence](2026-10-20-proot-full-gui.md) independently recorded Zink/Turnip on `:0`. These observations do not establish successful GPU draw/presentation for the full nested desktop.

## Existing Debian PRoot

A read-only `tx proot verify --distro debian --guest-user-from rootfs --display :1 --backend zink --json` completed with renderer `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, X11/audio reachable, and no guest write, package change, service action, or host lifecycle action. This confirms the individual Debian verifier workload on Native `:1`; profile ownership remains unverified and no config replay was performed.

A follow-up read-only run on 2026-10-20 used ./tx proot verify --distro debian --guest-user sbj --display :1 --backend zink. X11 and PulseAudio were reachable; GLX renderer class was zink_turnip with zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)); GLES context was OpenGL ES 3.2 Mesa 25.0.7-2+deb13u1 on the same renderer. The probe returned complete, but gles_draw_verified=false; it verifies backend/context detection for this fixed probe, not an actual application draw or presentation. Safety fields confirm no packages, services, or host GUI lifecycle changed. The existing PRoot and its running session were preserved.

A subsequent bounded draw check on Native display `:1` used the updated fixed verifier, which runs `timeout -s TERM 7s glxgears -info -geometry 180x100` only when both tools exist. It rendered 693 frames; the GLX workload itself reported `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, matching the requested Zink/Turnip renderer. The result reports `glx_draw=verified`, `glx_draw_frames=693`; the separate GLES draw field remains false. The diagnostic window timed out and closed, no `glxgears` process remained, and Native XFCE plus the existing Debian session stayed running. A final live rerun after adding the requested-renderer match guard returned `glx_draw=verified` with 486 frames and the same Zink/Turnip Adreno 825 renderer. No package, service, guest config, or host session lifecycle changed. This verifies an individual PRoot GLX draw on `:1`; it does not qualify GLES draw or nested Xephyr `:2` presentation.

A fresh nested XFCE run on Xephyr `:2` was queried with the updated structured verifier while live. X11 and PulseAudio were reachable; GLX renderer was unavailable; GLES context was verified as `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, OpenGL ES 3.2. The report remains `partial` and explicitly sets `gles_draw_verified=false`. GLX RGB visual creation, DRI3 presentation and an observable draw remain unavailable/unverified. Do not infer nested fullscreen acceleration from the GLES context string alone. The test's managed nested session was stopped afterward; Native XFCE `:1` stayed running.

## Verification

- `python3 -m unittest tests.test_graphics_management -v`: 9/9 passed, including GLES context-vs-draw reporting, forced-failure llvmpipe fallback, and rejection of an unqualified fallback renderer.
- `bash scripts/repo_test.sh`: 606/606 passed in 117.656 seconds on Native Termux. The suite includes the longer bounded fixture teardown allowance and the fresh-image digest rejection regression.
- Python compilation and `git diff --check` passed.

## Evidence

Live observations were captured through Native Termux SSH 8022. The nested context and presentation details are further described in [`2026-10-20-proot-full-gui.md`](2026-10-20-proot-full-gui.md).

The read-only PRoot verifier reports GLX and GLES separately, requires frame output and the requested renderer for GLX draw success, and never promotes an ES context to a draw result. Focused PRoot diagnostic tests passed 23/23 and graphics-manager tests passed 9/9 after this change.
