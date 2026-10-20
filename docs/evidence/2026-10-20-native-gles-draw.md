# Native GLES draw verification — 2026-10-20

Phase: P6 implementation evidence; the phase gate remains open.

## Result

The shared `graphics.provider.verify` service now verifies an actual Native OpenGL ES workload. On the Redmi Turbo 4 Pro (Android 16, aarch64, Adreno 825), `./tx mng graphics verify native gles :1 --json` returned `status=rendered`, `render_verified=true`, `context_verified=true`, renderer `Adreno (TM) 825`, and GLES `3.2 Mesa 26.3.0-devel (git-98f3d6229d)`. The 1280x720 surfaceless EGL pbuffer workload completed 1,098 shader frames over 5.000 seconds (219.47 frames/sec), with `glFinish()` after every frame. The manager correctly classified this renderer as accelerated.

This measures a synthetic off-screen shader workload. It does not measure Android screen presentation or the prior 120 Hz/120 FPS target, and it does not establish application compatibility or sustained thermal performance.

## Implementation

- The shared verifier checks the tracked GLES runner source for safe regular-file use and expected pbuffer/draw/finish calls.
- It compiles with Native `clang` into a unique private temporary directory under the Ternuxx state directory, with a 45-second compile bound; it runs fixed 1280x720, five-second parameters with a 15-second bound and removes the binary afterward.
- Success requires exit 0, an OpenGL ES 3 version, renderer identity, a positive completed-frame count, and positive measured throughput. `llvmpipe`/`softpipe` are reported as software by renderer classification.
- If `clang`, EGL/GLES link libraries, safe source, or a private state directory is unavailable, it does not claim a rendered result. Debian GLES remains unsupported by its current verifier.
- The CLI path uses the same shared service implementation; TUI, Web, and GTK call the same typed operation.

## Verification

- Focused graphics manager suite: 15/15 passed, including renderer/frame parsing, zero-frame rejection, and temporary binary cleanup.
- Full Native Termux repository suite: 612/612 passed.
- Python bytecode compilation passed for the modified Python modules.
- Live Native Termux command above passed on the already-running `:1` desktop without restarting GUI, changing backend selection, installing packages, or touching Debian PRoot.

## Limits and next work

The shared OpenGL software fallback remains verification-workload-only; ordinary application launches do not yet select an API-aware GPU/software backend. Nested Xephyr `:2` presentation, clean-install reproduction of the experimental KGSL candidate, NPU execution, and workload routing remain open. See the [GPU acceleration matrix](../testing/GPU-ACCELERATION.md).
