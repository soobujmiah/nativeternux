# Qualcomm Hexagon NPU inference

**Status:** platform silicon `DETECTED`; Ternuxx backend `NOT_IMPLEMENTED`; exact-device workload validation `UNKNOWN`. **Commercial class:** verified NPU inference is a `FREE_CORE` target.

## Feasibility evidence and limits

The dated device record identifies SM8735 / Adreno 825. Qualcomm's Snapdragon 8s Gen 4 product brief names a Hexagon NPU for SM8735. Upstream llama.cpp currently documents an **experimental** GGML Hexagon HTP backend with Android build/deployment examples, HTP logs, and benchmark/test examples on Snapdragon devices. Its docs enumerate HTP architecture library variants, but do not establish an SM8735-specific qualification or a Termux-app run for this phone. [Qualcomm product brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Product-Brief-Snapdragon-8s-Gen-4.pdf), [llama.cpp Snapdragon backend](https://github.com/ggml-org/llama.cpp/tree/master/docs/backend/snapdragon), [Hexagon developer notes](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/snapdragon/developer.md).

Google LiteRT has a Qualcomm QAIRT integration and Android deployment path; its Android app/runtime/library requirements are a separate architecture from a standalone Termux shell or Debian PRoot CLI. [LiteRT Qualcomm integration](https://github.com/google-ai-edge/LiteRT/tree/main/litert/vendors/qualcomm). Do not infer that an Android app delegate is callable from a Termux process.

No Hexagon SDK, runtime, model, compiled artifact or runner exists in this repo. No NPU runtime was installed or downloaded. The product's status is therefore not “NPU supported”; feasibility is now a researched candidate, with device/context/run blocked pending implementation and owner authorization.

## Qualification gates

1. Pin exact upstream runtime commit, build instructions, Hexagon SDK/tool versions, HTP architecture and target SoC support. Review licenses, notices, model distribution terms and package size before adding dependencies.
2. Establish one process context at a time: Android app, native Termux app process, or guest process. Record UID/sandbox, loader paths, required vendor libraries/FastRPC interface and permissions. No broad bind mounts, `LD_LIBRARY_PATH` hacks, root or Shizuku assumption.
3. Confirm backend registry shows HTP device/session and logs identify the HTP architecture. `QNN` library presence, NPU spec, `/dev` nodes, or session initialization alone are not success.
4. Run a small named model/workload and prove operator/tensor delegation to HTP. Save logs; list unsupported ops, partial CPU/GPU fallback, and offloaded fraction.
5. Verify output against CPU/reference with a defined numerical/task correctness check. Include repeatable failures and incorrect outputs as failed runs.
6. Compare CPU/GPU/NPU only under [the same-workload protocol](BENCHMARK-METHODOLOGY.md). Capture sustained latency/throughput, memory, thermal behavior and battery context; do not publish sample numbers copied from upstream docs as Ternuxx results.
7. Test restart, cancellation, memory pressure and fallback. Release qualification requires a sustained repeated run, no crash/data corruption, supported model/license and exact device profile.

NNAPI should not be selected as the default future foundation: Android documents its deprecation from Android 15. That does not itself make QNN/HTP unusable; choose only a currently supported, specifically verified runtime path.
