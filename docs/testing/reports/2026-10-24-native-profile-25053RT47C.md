# Native Termux profile observation — 2026-10-24

**Evidence class:** direct, read-only observation of the active Native Termux session.
Phase: `P5`
**Repository base:** `33a465c` (`main`); the worktree contains uncommitted changes.
**Observation time:** 2026-10-23 23:56 UTC / 2026-10-24 05:56 Asia/Dhaka.
**Scope:** the owner's current device and installed Native Termux environment. This record does not certify other devices or a public release.

## Evidence

Direct command output is retained in the active session; repository records include only non-secret observations. Reproduction commands and observed values follow.

## Host and Termux profile

| Component | Observed value |
|---|---|
| Device model | `25053RT47C` |
| Android release / API | Android 16 / API 36 |
| Android security patch | 2026-03-01 |
| ABI | Android `arm64-v8a`; Termux package architecture `aarch64` |
| Kernel | Linux `6.6.77-android15-8-g4a507830d890-ab13636293-4k`, aarch64 |
| Termux app | F-Droid build `0.119.0-beta.3` |
| Termux prefix | `/data/data/com.termux/files/usr` |
| Termux:X11 package | `termux-x11-nightly 1.03.01-6` |
| Termux:X11 Android app | Installed; version could not be read because Android PackageManager dump permission is unavailable to the Termux app UID |
| XFCE session manager | `xfce4-session 4.20.4-1` |
| Python | `3.14.6-1` |
| Main package source | `https://termux.danyael.xyz/termux/termux-main stable main` |
| X11 package source | `https://termux.danyael.xyz/termux/termux-x11 x11 main` |

The package index lists newer candidates than several installed packages. This snapshot records installed versions and does not authorize a package upgrade.

## Current Native desktop and audio

- `tx status --json` reported display `:1`, with the Ternuxx supervisor, X11, and XFCE session live. Android GUI visibility was `unknown`; no visual acceptance is claimed by this command.
- `termux-x11-nightly` is the exact Native X11 package observed for this session. The companion Android APK version could not be obtained with the app's available permissions.
- The installed `pulseaudio` package is `17.0-4`; `pactl info` reported a local daemon as `17.0-dirty`, server protocol 35, and default sink `OpenSL_ES_sink`. Ternuxx Doctor reported its authenticated loopback endpoint ready. This proves client/server readiness, not audible output or quality.

## Graphics and compute boundary

`tx doctor --graphics --json` was run with `DISPLAY=:1` at this snapshot time. It detected `/dev/kgsl-3d0` and the `Adreno825` model, reported no renderer string in its generic finding, and showed a Vulkan probe warning: the installed `vulkaninfo` binary could not link because `_ZNSt6__ndk113__hash_memoryEPKvm` was unavailable. At that doctor snapshot, the probe did not establish Vulkan initialization or a rendered workload. A later direct API-specific recheck is recorded in [P6 graphics evidence](../../evidence/2026-10-24-native-graphics-fallback-recheck.md). That report preserves the initial failure and records a follow-up fix that passes a bounded Adreno 825 Vulkan draw. Neither result establishes inference, general application correctness, thermal stability, or release qualification. No package upgrade or driver change was attempted.

Doctor reported eight logical CPUs. CPU is available as the Native execution substrate, but this repository has no inference runtime, model loader, or inference correctness/benchmark report. NPU libraries are discovery hints only; no usable runtime or workload was observed.

## Qualification decision

This is the sole directly observed Native Termux target profile in this repository. The Native desktop lifecycle and authenticated local audio endpoint were live; graphics workload and physical audio output remain unqualified; boot delivery and inference remain unverified/not implemented. Other Android versions, device models, ABIs, Termux release channels, repository origins, displays, and audio/graphics stacks remain **unqualified candidates**. The record is an exact compatibility baseline, not a general support promise or release qualification.

## Reproduction checks

These read-only checks produced the observations above:

```sh
uname -a
getprop ro.build.version.release
getprop ro.build.version.sdk
getprop ro.build.version.security_patch
getprop ro.product.model
termux-info
pkg show termux-x11-nightly xfce4-session pulseaudio mesa-vulkan-icd-freedreno
./tx status --json
DISPLAY=:1 ./tx doctor --graphics --json
pactl info
```

The `pactl info` output contains a cookie; do not store or publish that field. The artifact records only non-secret server readiness/version/sink fields.


Gate: PASS

## Acceptance criteria

- The exact currently observed Android, API, ABI, device model, Termux release, package sources, X11 package, XFCE package, audio package/server, and selected display are recorded with unavailable values explicitly marked.
- The only directly observed target profile is distinguished from untested compatibility candidates.
- Desktop lifecycle, audio endpoint readiness, graphics probe result, CPU/inference boundary, and boot-delivery limits are separated; no unsupported GPU/NPU or release claim is made.
- Read-only device checks completed without stopping the Termux app, active desktop, or Native services and without reading shared/external storage.
