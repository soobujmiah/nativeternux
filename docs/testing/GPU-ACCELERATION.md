# GPU inference acceleration

**Status:** inference integration `NOT_IMPLEMENTED`; stock Native Termux renderer `SOFTWARE (llvmpipe)`; isolated community KGSL GL trial `PASS (Adreno 825)`; GPU inference workload `UNKNOWN`. **Commercial class:** supported GPU inference is a `FREE_CORE` target.

## Context-separated evidence

The default Native Termux Mesa/Freedreno probe on Adreno 825 still returns `VK_ERROR_INCOMPATIBLE_DRIVER`, and ordinary `DISPLAY=:1 glxinfo -B` reports `llvmpipe (LLVM 21.1.8, 128 bits)`, `Accelerated: no`. The installed Native DRI directory contains `zink_dri.so` but no `kgsl_dri.so`. Separately, owner-authorized testing of a third-party draft KGSL/Turnip build from Native Termux on the same `:1` display, with only that process pointed to an extracted candidate prefix, enumerated Adreno 825 and reported Freedreno / `Accelerated: yes`; a bounded `glxgears` workload drew 602 frames in 5.0 seconds (~120.280 FPS) while the running XFCE compositor was verified on. The current XFCE/GTK session was not restarted and still uses the stock llvmpipe path. The Debian PRoot Zink/Turnip route remains separate and cannot supply Bionic libraries. No Native Mesa package or shared system library was replaced. See the [dated isolated driver trial](../evidence/2026-10-20-workstation-qualification-execution.md#native-kgslturnip-community-build-trial--2026-10-20). Native GPU inference remains unverified.

Upstream llama.cpp's Snapdragon backend docs describe GPUOpenCL on Adreno alongside CPU and Hexagon HTP, and contain Android target build/run examples. This makes Snapdragon/OpenCL a research candidate distinct from the failing Vulkan probe. It remains untested on this exact SM8735 device, native Termux app context and Ternuxx code. See [upstream Snapdragon backend](https://github.com/ggml-org/llama.cpp/tree/master/docs/backend/snapdragon) and [general Android/Termux instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md).

## What counts as GPU success

- Build and dependency versions are recorded; runtime starts without loader errors.
- GPU device is identified, and runtime logs show the target operations/tensors actually delegated. Record delegated and CPU-resident work separately.
- Same model/hash, quantization, prompts, context, output limits, runtime commit and test conditions are run on CPU and GPU.
- Output passes the same correctness checks. If outputs differ numerically, record tolerances/reference; do not use subjective response quality as proof.
- Benchmark includes load time, TTFT/prompt throughput, decode tokens/s, end-to-end time, memory, repeat variation, thermal state and failures as available.
- Forced-GPU execution that silently falls back to CPU is a GPU `FAIL` or `PARTIAL`, not a pass. CPU fallback remains a separately tested free path.
- Sustained behavior and safe process teardown pass before release qualification.

The stock package route still fails on this Adreno 825. The third-party process-scoped Mesa candidate does pass a short same-display GLX workload; that does not establish that the running XFCE session uses it, that sustained rendering is stable, or that inference is accelerated. The owner-directed next step is a same-display session-level trial after saving GUI work; the existing llvmpipe environment remains intact and VirGL remains a separate unqualified PRoot path. GPU inference needs a named model/runtime workload and delegated-operation evidence.
