# Native and Debian graphics live recheck — 2026-10-20

Phase: `P4`
Phase: `P6`

## Native Termux

On the live Adreno 825 device, `tx mng graphics verify native opengl :1` completed an off-screen glmark2 run with renderer `Adreno (TM) 825`, score 581, and `render_verified=true`. `tx mng graphics verify native gles :1` created an OpenGL ES 3.2 context with the selected KGSL candidate and renderer `Adreno (TM) 825`; the API explicitly reports context-only evidence and does not claim a draw. Vulkan enumerates the device, but no Vulkan draw was verified.

A safe deliberate failure used an isolated empty graphics state and the intentional invalid `GALLIUM_DRIVER=ternuxx-intentional-missing-driver` value. The OpenGL primary attempt exited 1; the verifier then rendered off-screen using `llvmpipe (LLVM 21.1.8, 128 bits)`, score 109, and returned `fallback-rendered`, `accelerated=false`. This verifies the manager's bounded OpenGL verification fallback on this device. It does not yet retry ordinary application launches or choose per-workload GPU/NPU backends. NPU runtime and clean-install driver reproduction remain unverified.

A plain `es2_info` invocation without the saved candidate context reported llvmpipe and DRI3/Zink initialization warnings. The managed GLES probe, which loads the exact selected candidate path, reported Adreno instead. An `es2gears_x11` window could not be observed under the tested X11 route; an actual GLES draw/presentation therefore remains unverified.

The owner reports that Debian XFCE's device information displayed the GPU on standalone `:0`, and that Native XFCE is visible on the Android screen. Earlier live verification in [the full GUI evidence](2026-10-20-proot-full-gui.md) independently recorded Zink/Turnip on `:0`. These observations do not establish successful GPU draw/presentation for the full nested desktop.

The owner reports that Debian XFCE's device information displayed the GPU on standalone `:0`, and that Native XFCE is visible on the Android screen. Earlier live verification in [the full GUI evidence](2026-10-20-proot-full-gui.md) independently recorded Zink/Turnip on `:0`. These observations do not establish successful GPU draw/presentation for the full nested desktop.

## Existing Debian PRoot

A read-only `tx proot verify --distro debian --guest-user-from rootfs --display :1 --backend zink --json` completed with renderer `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, X11/audio reachable, and no guest write, package change, service action, or host lifecycle action. This confirms the individual Debian verifier workload on Native `:1`; profile ownership remains unverified and no config replay was performed.

A fresh nested XFCE run on Xephyr `:2` was queried with the updated structured verifier while live. X11 and PulseAudio were reachable; GLX renderer was unavailable; GLES context was verified as `zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP))`, OpenGL ES 3.2. The report remains `partial` and explicitly sets `gles_draw_verified=false`. GLX RGB visual creation, DRI3 presentation and an observable draw remain unavailable/unverified. Do not infer nested fullscreen acceleration from the GLES context string alone. The test's managed nested session was stopped afterward; Native XFCE `:1` stayed running.

## Verification

- `python3 -m unittest tests.test_graphics_management -v`: 9/9 passed, including GLES context-vs-draw reporting, forced-failure llvmpipe fallback, and rejection of an unqualified fallback renderer.
- `bash scripts/repo_test.sh`: 596/596 passed in 102.351 seconds on Native Termux. The first full run had one fixture teardown timeout at its existing 8-second limit; the test passed in isolation, so fixture cleanup was raised to a still-bounded 20 seconds and the full suite passed.
- Python compilation and `git diff --check` passed.

## Evidence

Live observations were captured through Native Termux SSH 8022. The nested context and presentation details are further described in [`2026-10-20-proot-full-gui.md`](2026-10-20-proot-full-gui.md).

The read-only PRoot verifier now reports GLX and GLES context separately and never promotes an ES context to a draw result. Focused PRoot diagnostics and graphics tests passed 31/31 after this change.
