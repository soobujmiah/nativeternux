# Current testing and acceleration limitations

**Last reconciled:** 2026-10-20 against repository source and dated evidence. Refresh these statements after accepted test reports or code changes.

- Ternuxx is a Bash desktop/lifecycle manager; no inference runtime, model loading, CPU/GPU/NPU backend, public inference API, or model example is implemented.
- The repository contains no product tests or inference benchmark harness. Existing CI checks deterministic repository metadata, bridge content and classification only; it cannot validate Android device behavior.
- CPU inference has no selected or integrated runtime and has no correctness/performance evidence. CPU is the free-core target, not a currently shipped feature.
- The stock Native Turnip ICD probe returned `VK_ERROR_INCOMPATIBLE_DRIVER`; the selected experimental KGSL/Freedreno candidate has since passed a bounded 120-frame Vulkan draw on `:1`. This is not Vulkan inference, broad application qualification, sustained/thermal qualification, or clean-install reproducibility.
- Upstream llama.cpp documents Android/Snapdragon OpenCL and experimental Hexagon backends, but exact SM8735 support, Termux-app operation, Ternuxx integration, correctness and stability are unverified.
- Qualcomm's product brief confirms Hexagon NPU silicon for SM8735 platform. Runtime presence, FastRPC/session permission, selected operators, model correctness and performance in Termux are unknown. Android app LiteRT/QAIRT requirements do not transfer automatically to native shell or PRoot.
- Existing Ternux PRoot Zink/Turnip is a separately configured desktop graphics path; its current live renderer was not rerun in this project, and it provides no AI inference proof.
- No compatibility combination is release-qualified. No download/release artifact or signed test report exists.
- Device information is a dated owner-device profile; no present-day device test was run for this audit. No accelerator timings, tokens/s, speedups, power estimates, thermal claims, or customer results are available.

Use `UNKNOWN` for missing evidence, `BLOCKED` when an implementation/prerequisite prevents a test, and `FAIL` only for an executed failed criterion. Never turn unknown into zero, unsupported, or success without new evidence.
