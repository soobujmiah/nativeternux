# Workload performance and optimization

Ternuxx does not currently provide named `efficiency`, `balanced`, `sustained`, or custom optimization profiles. It does not change Android CPU/GPU clocks, thermal policy, governors, or hidden system properties.

The implemented graphics controls are narrower: Native graphics diagnostics, API-specific bounded render checks, Native backend selection for future desktop starts, and a verified software-rendering fallback. Current results and their exact limits are in the [Native graphics report](testing/GPU-ACCELERATION.md). A renderer result from an off-screen test is not an application FPS or battery claim.

## Safe qualification standard

Before adding a workload tuning control, record the named workload, exact device and software profile, selected backend, input/output correctness, baseline and changed settings, memory use, thermal/battery context, duration, and repeat variation. Preserve a CPU/software fallback and report when it is used. Do not silently switch backends or call detection a pass.

Any future configuration change must name its scope and original value, use a reviewable plan, and have a tested restore path. Ternuxx must never disable Android thermal protections, raise hidden clock limits, pin work to guessed CPU cores, or release a wake lock owned by another service.

## Not implemented

- General per-workload optimization profiles or telemetry dashboard.
- AI inference runtime, model selection, CPU inference baseline, or GPU/NPU delegation.
- Automated thermal or battery control.
- Cache cleanup or storage optimization.

These require separate implementation and qualification. See the [phase roadmap](ROADMAP.md), [CPU baseline](testing/CPU-BASELINE.md), and [NPU feasibility](testing/NPU-ACCELERATION.md).
