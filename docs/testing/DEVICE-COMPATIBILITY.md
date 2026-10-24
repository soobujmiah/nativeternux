# Device and backend compatibility

## Qualification rule

A device is a qualified Ternuxx target only for the named capabilities and exact software profile that have direct evidence. A detected device node, package, renderer name, or successful desktop launch does not establish accelerated workload support or release readiness.

The only current Native Termux profile directly observed in this repository is the owner's Android 16 `25053RT47C` device, ABI `arm64-v8a`, with Termux `0.119.0-beta.3`. Exact package, display, audio, graphics, and evidence limits are recorded in the [dated profile observation](reports/2026-10-24-native-profile-25053RT47C.md).

## Capability stages

| Capability | Current evidence | Qualification |
|---|---|---|
| Native Termux environment | Android 16/API 36, `arm64-v8a`, Termux `0.119.0-beta.3` observed | One device/profile observed; not generalized |
| Native desktop | Ternuxx supervisor, X11, and XFCE live on `:1` | Lifecycle live; Android GUI visibility not confirmed in this snapshot |
| Native audio | Authenticated local PulseAudio endpoint ready; default sink `OpenSL_ES_sink` | Endpoint readiness only; physical audibility/quality not tested |
| Native graphics | Bounded OpenGL/GLES draws and a 120-frame Vulkan `vkcube` draw use Adreno 825; llvmpipe fallback renders | Exact workloads only on the experimental candidate; see [direct P6 recheck](../evidence/2026-10-24-native-graphics-fallback-recheck.md); no general application or inference claim |
| CPU inference | CPU available; no Ternuxx inference runtime/model/test | Not implemented |
| NPU inference | Vendor libraries visible; usable runtime and workload absent | Unverified; not implemented |
| Boot/recovery delivery | Termux:Boot package and receiver detected, OS delivery policy unknown | Cold-boot delivery unverified |

Other devices, Android releases, ABIs, Termux channels, package sources, display servers, and audio/graphics combinations remain unqualified until separately tested. Current package versions are snapshots and can change independently of this document.

## Evidence requirements

A new device or backend qualification needs the exact device/Android/ABI and Termux profile, package and driver versions, selected display/audio context, named workload, correctness method, captured results, failures, and evidence provenance. Keep unknown values explicit. A GPU or NPU claim additionally needs initialized backend access and a correct representative workload; a release claim needs repeated performance, thermal, stability, and recovery evidence.
