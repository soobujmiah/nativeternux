# Workload optimization

Ternuxx should improve useful work per watt and keep performance sustainable. An optimization result is measured against a named workload and device state; a “boost” label alone is not evidence.

## Optimization profiles

Planned profiles are `efficiency`, `balanced`, `sustained`, and `custom`. A profile changes only settings that Ternuxx can identify, scope to one workload/session, explain, and restore. A higher performance preference is offered only when the device/runtime exposes a supported control; Ternuxx will not force hidden Android settings to simulate one.

The profile registry records provider (native or existing Debian PRoot), workload, selected backend, supported knobs, original values, applied values, and restore steps. Profile changes are previewed, saved to the operation journal, and reversible. Profiles are not mixed across providers unless an explicit hybrid workload rule says so.

## Workload controls

Where the application supports the setting, optimization may tune:

- CPU worker/thread count and parallel job limits;
- model context, batch size, quantization choice, and memory ceiling for a verified AI runtime;
- render resolution, frame-rate cap, texture/quality settings, and shader-cache budget;
- native versus PRoot provider and a renderer already proven for that workload;
- background task concurrency, with a safe pause/reduce action when the device reports thermal stress.

An accelerator is never forced just because a library, device node, or environment variable exists. A failed or unknown GPU/NPU path remains visibly unavailable; it does not silently become an unreported software path.

## Thermal, battery, and memory awareness

`ternuxx optimize status` should report the evidence available to the current environment: battery state, Android thermal state when a supported companion API supplies it, memory pressure, workload thread count, provider, renderer, and recent task performance. Missing telemetry is shown as unavailable. A Termux shell temperature file is not treated as a portable Android Thermal API.

When supported telemetry says the device is under sustained thermal pressure, the controller may offer or apply an owner-enabled per-workload reduction, such as fewer worker threads, smaller model batches, lower render quality, or pause. It must not disable Android thermal protections, raise hidden clock limits, pin work to guessed CPU cores, or hold a wake lock after the selected task ends.

Wake locks are scoped to an explicit job/session with a visible reason and owner. The manager releases its own lock on normal exit and uses journal recovery to identify a lock left by an interrupted job. It never releases another app's wake lock.

## Storage and cache management

`ternuxx optimize storage` reports size and ownership before proposing cleanup. By default, cleanup may target only Ternuxx-owned temporary files or caches whose safe regeneration is documented. It previews exact paths and expected space before requiring confirmation. It never prunes the existing Ternux Debian rootfs, removes user files, runs package autoremove, or deletes shader/model caches without explaining the rebuild cost and asking separately.

No size saving is promised until measured. Profile and cache reports distinguish Termux app-private storage, Ternuxx state, the existing Ternux rootfs, and shared Android storage.

## System-level controls

CPU governor changes, GPU clock/voltage changes, thermal-service overrides, `setprop`, sysfs writes, Android debugging toggles, and broad process killing are outside automatic optimization. If a later device-specific integration proposes a privileged control through Shizuku or root, it requires a separate opt-in, exact before/after preview, supported-device evidence, rollback, and a dedicated safety review. It must never bypass thermal safeguards.

## Measurement and acceptance

Every optimization claim records device/OS, package and model versions, provider, backend, workload input, output correctness, cold/warm latency or throughput, peak memory, battery/thermal state, and test duration. Compare an unchanged baseline with the selected profile under similar starting conditions. Long-running tests are necessary for sustained-performance claims because short runs can hide later thermal throttling.

Optimization is successful when it improves the stated target (for example, latency, sustained throughput, battery use, or memory) without breaking correctness, exceeding the declared thermal/memory limits, changing another provider, or leaving state behind. The user can inspect, disable, and restore every profile.

## Wine/Hangover workloads

Native Wine/Hangover is an optional app runtime, not a device-wide acceleration switch. Prefer native ARM64 Windows binaries when the app provides them; translated x86/x86-64 execution has workload-specific overhead and compatibility limits. CPU is the baseline. Graphics backend selection is per application: validate WineD3D/OpenGL independently, and require Vulkan 1.3 plus the required features and a successful real workload before offering DXVK. The current recorded native Vulkan probe failed on this device, so native DXVK is not an available optimization claim yet. The existing PRoot Zink/Turnip path remains a distinct provider.

NPU acceleration requires an application/runtime path that demonstrably submits supported inference to the NPU. Wine/Hangover alone does not supply that bridge. Keep Windows AI workloads on CPU unless a named runtime integration is verified. See [Native Wine and Hangover](WINE-NATIVE.md) for the support gate and management contract.
