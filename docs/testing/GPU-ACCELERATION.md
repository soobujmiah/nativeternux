# GPU inference acceleration

**Status:** integration `NOT_IMPLEMENTED`; native Vulkan probe `FAIL` for one recorded configuration; inference workload `UNKNOWN`. **Commercial class:** supported GPU inference is a `FREE_CORE` target.

## Context-separated evidence

The recorded native Termux Mesa Freedreno/Turnip probe on Adreno 825 returned `VK_ERROR_INCOMPATIBLE_DRIVER`. A direct Native Termux `DISPLAY=:1 glxinfo -B` run on 2026-10-20 reported `llvmpipe (LLVM 21.1.8, 128 bits)`, `Accelerated: no`; the Native XFCE/`xfce4-about` context therefore is not GPU-rendered by the current observed path. The installed Native DRI directory contains `zink_dri.so` but no `kgsl_dri.so`; Zink cannot initialize because the current Native Turnip ICD rejects GPU ID 6830. The separate Debian PRoot Mesa 25.0.7 Zink/Turnip route does render Adreno 825, but its glibc libraries cannot be substituted into Native Termux/Bionic. No package/driver change has been applied. Native GPU workload/inference remains unverified.

Upstream llama.cpp's Snapdragon backend docs describe GPUOpenCL on Adreno alongside CPU and Hexagon HTP, and contain Android target build/run examples. This makes Snapdragon/OpenCL a research candidate distinct from the failing Vulkan probe. It remains untested on this exact SM8735 device, native Termux app context and Ternuxx code. See [upstream Snapdragon backend](https://github.com/ggml-org/llama.cpp/tree/master/docs/backend/snapdragon) and [general Android/Termux instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md).

## What counts as GPU success

- Build and dependency versions are recorded; runtime starts without loader errors.
- GPU device is identified, and runtime logs show the target operations/tensors actually delegated. Record delegated and CPU-resident work separately.
- Same model/hash, quantization, prompts, context, output limits, runtime commit and test conditions are run on CPU and GPU.
- Output passes the same correctness checks. If outputs differ numerically, record tolerances/reference; do not use subjective response quality as proof.
- Benchmark includes load time, TTFT/prompt throughput, decode tokens/s, end-to-end time, memory, repeat variation, thermal state and failures as available.
- Forced-GPU execution that silently falls back to CPU is a GPU `FAIL` or `PARTIAL`, not a pass. CPU fallback remains a separately tested free path.
- Sustained behavior and safe process teardown pass before release qualification.

The failed Vulkan probe blocks that exact route. It does not pre-judge OpenCL, other Mesa revisions, Android framework runtimes or the Ternux PRoot route. These need individually named test entries; do not combine them into a generic “GPU accelerated” badge.
