# Device and backend compatibility

**Authority:** accepted reports under `reports/` and corresponding entries in [`FEATURE-MATRIX.yaml`](FEATURE-MATRIX.yaml). This page summarizes the only recorded device snapshot and clearly separates inference from desktop graphics.

## Recorded profile

| Device/profile | Android / ABI | CPU | GPU | NPU silicon | Native graphics evidence | Inference evidence | Qualification |
|---|---|---|---|---|---|---|---|
| `25053RT47C` (`onyx`), owner device | Android 16 / `aarch64` (Termux `0.119.0-beta.3` in dated record) | Present; no Ternuxx inference runtime/test | Adreno 825, SoC SM8735 | Qualcomm product brief identifies Hexagon NPU for Snapdragon 8s Gen 4 / SM8735 platform; device runtime access untested | Native Termux `vulkaninfo --summary` failed with `VK_ERROR_INCOMPATIBLE_DRIVER` on recorded Mesa 26.2.4; native live OpenGL renderer not recorded | No CPU, GPU, or NPU inference test/report in this repo | `DETECTED`; no inference `WORKLOAD_VERIFIED` or `RELEASE_QUALIFIED` |

The device row is based on the dated read-only observation in [`RESEARCH.md`](../RESEARCH.md), not a new physical-device session. Android/Termux version, package version, or driver may have changed since then. It must not be generalized to other Adreno/Qualcomm devices.

## Separate Ternux provider evidence

The independent Ternux project documents CPU/Vulkan llama.cpp inference on this device through its Debian PRoot setup, plus experimental Hexagon HTP and QNN routes. This is evidence about the separate Ternux provider, not a Ternuxx adapter or a Ternuxx release qualification. The HTP record includes correctness failures and incomplete operator coverage; the QNN image record still lacks independent stage-tensor correctness. See the [master audit's external-provider matrix](../evidence/PHASE-0-MASTER-AUDIT.md#5-ai-runtime-and-provider-inventory) and [Ternux accelerator release plan](https://github.com/soobujmiah/ternux/blob/main/docs/ACCELERATOR-RELEASE-PLAN.md).

## Backend stage matrix

| Context/backend | Detected | Initialized | Workload verified | Correctness | Performance | Stability/thermal | Release qualified |
|---|---|---|---|---|---|---|---|
| Native Termux CPU inference | `UNKNOWN` (no inference integration) | `BLOCKED` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NO` |
| Native Termux GPU / recorded Vulkan Turnip probe | GPU silicon detected; tested ICD probe `FAIL` | Vulkan physical-device setup `FAIL` for recorded package/process | `UNKNOWN` for all inference workload | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NO` |
| Native Termux Snapdragon OpenCL inference candidate | Platform GPU detected | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NO` |
| Native Termux Hexagon HTP inference candidate | Platform silicon documented | `UNKNOWN` in Termux app context | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NO` |
| Existing Ternux PRoot Zink/Turnip desktop route | Source/configuration reviewed; live renderer not rerun in this audit | Owner reports it has worked; no fresh check in this project | No AI inference workload evidence | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | Not a Ternuxx inference release |
| LiteRT/QAIRT Android app integration candidate | Upstream integration documentation exists | `UNKNOWN` on this device/app | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `NO` |

`FAIL` above is narrowly limited to the exact native Vulkan probe described in `RESEARCH.md`; it is not a verdict on all Android GPU APIs. `DETECTED` means a platform component is identified, not that the process can access it.

## Report acceptance

Add a row or report only when it includes device/model identifier appropriate to privacy policy, Android build, Termux/PRoot context, runtime and driver revisions, model hash/license, exact backend logs, workload and correctness method, raw measurements, repeats, failures, and owner-operated versus automated provenance. Unknown fields stay `UNKNOWN`. See [report template](reports/REPORT-TEMPLATE.md).
