# Native NPU feasibility

**Current status:** Ternuxx has no NPU runtime, model runner, or NPU workload implementation. NPU availability is not established for the current Native Termux process.

## Current device observation

Ternuxx Doctor identified the Adreno 825 platform and some Android vendor libraries, but found no candidate FastRPC device nodes and no known runtime command-line tool. Library visibility and platform documentation are discovery hints only; they do not prove the Termux app can open an NPU device or delegate work. The latest device snapshot is in the [Native profile report](reports/2026-10-24-native-profile-25053RT47C.md).

No NPU package was installed, no permissions were broadened, and no workload was attempted. NPU acceleration remains **unverified and not implemented**; the CPU/Native desktop path remains usable without it.

## Requirements before implementation

1. Identify a maintained runtime with explicit support for the exact SoC and Native Termux process context.
2. Review runtime, SDK, model, and binary licenses, provenance, size, and update path.
3. Demonstrate least-privilege device/runtime access without root, Shizuku, broad mounts, or loader-path hacks.
4. Run a named workload and record backend delegation, CPU fallback, correctness against a reference, cancellation, memory, thermal behavior, and repeat results.
5. Keep the feature unavailable until the full exact-device path passes; do not infer support from silicon, libraries, or external Ternux results.

Older research about the independent Ternux guest is historical context and does not establish a Ternuxx Native adapter or capability.
