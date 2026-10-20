# Graphics and accelerator verification

## Current device results

Target: Native Termux on Android 16, aarch64, Adreno 825. Results below are scoped to the named API, process, and display. They do not establish inference acceleration or general application compatibility.

| Provider and API | Current result | What the evidence establishes |
|---|---|---|
| Native OpenGL | Verified on display `:1`; Adreno 825 / Freedreno reports `Accelerated: yes` | The selected local Mesa KGSL candidate rendered GLX and the bounded `glmark2` workload. The stock Mesa path uses llvmpipe when the candidate is not selected. |
| Native OpenGL ES | Shared manager rendered 1,098 frames in five seconds (219.47 frames/sec) at 1280x720; GLES 3.2; Adreno 825; `accelerated=true` | The tracked surfaceless EGL/GLES runner drew a shader to a pbuffer with `glFinish` each frame. This is synthetic off-screen throughput, not presented UI FPS. The verifier compiles into private temporary state and removes the binary after the run. |
| Native Vulkan | Adreno 825 rendered the bounded 120-frame `vkcube` workload through the selected candidate | Vulkan device enumeration and selected draw device matched. Stock ICD separately returned `VK_ERROR_INCOMPATIBLE_DRIVER`. |
| Debian OpenGL | Verified through the existing guest on `:1`; Zink over Turnip reports Adreno 825 | Existing Debian glibc stack only. The fixed verifier is read-only and does not install or alter guest files. |
| Debian OpenGL ES | Unavailable through the current adapter | The guest verifier checks OpenGL/Zink, not a GLES workload. |
| VirGL | Unqualified | A Native server process or available package alone does not prove a guest VirGL renderer. |
| GPU inference / NPU | Not implemented or verified | No model/runtime workload has demonstrated delegated execution. |

The current desktop preference is stored in private Ternuxx state. The running GUI session may continue to use the environment it inherited at its last start; changing the preference applies to future starts. Fresh installs use system Mesa because the locally tested candidate has no completed installer or clean-install qualification. The candidate remains experimental.

## Shared management commands

```sh
./tx mng graphics status native
./tx mng graphics status debian
./tx mng graphics verify native opengl
./tx mng graphics verify native gles
./tx mng graphics verify native vulkan
./tx mng graphics select native system
./tx mng graphics select native kgsl-freedreno
```

OpenGL verification runs a bounded off-screen-mode `glmark2` workload. If the selected accelerated path fails, it tries software in order: `llvmpipe`, then `softpipe`; it only reports fallback success when the renderer matches the attempted backend. This is verification-workload behavior and is not yet wired into ordinary app launches. Vulkan verification runs a bounded 120-frame `vkcube` draw on the active X11 display. It reports rendered only when the workload-selected GPU matches `vulkaninfo`; absent display/tool remains enumeration-only. Native OpenGL ES verification builds the checked-in GLES 3 pbuffer source with `clang` into the private Ternuxx state directory, runs a bounded shader draw, then cleans up the temporary binary. It returns `unavailable` if clang, source, EGL/GLES development libraries, or a private state directory is missing. Debian GLES remains unavailable through the current adapter. The Debian adapter supports only its configured OpenGL/Zink read-only check. CLI, TUI, Web, and GTK send these operations to the shared management service; action coverage varies by client.

To use stock Native Mesa for the next desktop start, select `system`. To use the verified candidate for future starts, select `kgsl-freedreno`. Neither operation restarts the current desktop. The selected candidate must already exist in private provider state. This checkout does not yet download or install it on a fresh device.

## Repeatable test setup and limits

The Native candidate came from a GitHub Actions artifact for the community draft [lfdevs/termux-packages PR #25](https://github.com/lfdevs/termux-packages/pull/25), not an official Termux release, and was staged under `$TERNUXX_STATE_DIR/graphics/providers/native-mesa-0219ff84/`. The checked-in profile records its draft PR commit, workflow run, package names, versions, and hashes, but does not include the binary artifact or a stable distribution URL. Do not download an unverified replacement based only on the PR; a Ternuxx provider installer needs an owner-approved, reproducible artifact source and provenance review. A Ternuxx preview-first provider installer is still required for clean-install reproducibility.

The checked-in evidence records the device package versions, candidate and stock measurements, display mode, and failure cases:

- [Native candidate and session qualification](../evidence/2026-10-20-workstation-qualification-execution.md)
- [Native off-screen benchmark results](../evidence/2026-10-20-native-offscreen-glmark2.md)
- [KGSL session selection](../evidence/2026-10-20-native-kgsl-session-selection.md)
- [Shared graphics manager and client coverage](../evidence/2026-10-20-shared-graphics-manager.md)
- [Native GLES draw verification](../evidence/2026-10-20-native-gles-draw.md)
- [Debian adapter audit and current adoption record](../evidence/2026-10-20-ternuxx-proot-consolidation.md)

## GPU inference requirements

A GPU inference pass requires a named model/runtime, recorded binary and model hashes, target-device identification, runtime logs showing delegated operations, correctness checks, and comparable CPU/GPU timing. A forced-GPU run that falls back silently to CPU is not a GPU pass. Record load time, prompt and decode throughput, memory, repeat variation, thermal behavior, and failure/teardown behavior where available. NPU capability claims require the same workload-level evidence.

Upstream llama.cpp describes Snapdragon/OpenCL and Hexagon HTP backends as research options; their existence does not show that they work in this Ternuxx runtime. See [llama.cpp Snapdragon backend](https://github.com/ggml-org/llama.cpp/tree/master/docs/backend/snapdragon) and [Android/Termux instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md).
