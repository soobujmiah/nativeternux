# Native Wine and Hangover research

**Status: not implemented or supported.** This page records Native Termux research for a possible Wine/Hangover catalog entry. There is no Ternuxx Wine install, run, prefix, or recovery action. Package candidates and compatibility claims require a fresh device-local preview and workload test before implementation.

## What the runtime can do

Wine is a Windows API compatibility layer. Hangover extends ARM64 Wine so it can run selected x86 and x86-64 Windows applications on ARM64 Linux by emulating application code while keeping Wine and Unix-side work native where possible. The upstream project documents ARM64EC with FEX for x86-64 and emulator options for 32-bit x86. It also says ARM64 Windows applications can run without CPU emulation when the required runtime components are available. These facts describe the upstream design; they do not certify a particular application, Termux package build, or device workload.

The read-only Termux package index on this device currently lists `hangover`, `hangover-wine`, `hangover-libarm64ecfex`, `hangover-libwow64fex`, and `hangover-wowbox64` at candidate version 11.16 in the Termux:X11 repository. All five are currently not installed. The configured TUR index also contains older 10.0-1 candidates, so the manager must show source and version and must not silently mix repositories. The index is time-sensitive, so Doctor and the installer must re-query the configured official package indexes before proposing a package transaction. A package listing is candidate evidence only. Official Termux package issue reports include version-specific x86/x86-64 launch failures and package-update build failures; these reports do not establish that 11.16 is broken, but they make a real smoke test and explicit source/version reporting mandatory. Do not silently add an unreviewed repository or download an unofficial binary if a package is missing.

## Separate the execution and graphics paths

- **CPU:** CPU execution is the baseline. Prefer a compatible ARM64 Windows build where available; x86/x86-64 apps need translation and can be slower or incompatible. Tune worker counts only per app and workload, with sustained thermal and memory measurements.
- **Native display:** Windows windows should use the selected native Termux:X11 display and native Termux libraries. An experimental renderer result does not establish the native Wine renderer.
- **OpenGL:** WineD3D/OpenGL is a candidate path only after a real application reports the expected renderer and renders correctly. Presence of Mesa libraries is not proof.
- **Vulkan/DXVK:** Hangover upstream states that DXVK needs Vulkan 1.3 and required features. On this device, the recorded native Termux Vulkan probe returned `VK_ERROR_INCOMPATIBLE_DRIVER` for the Adreno 825 with the tested native driver. Therefore Ternuxx must currently report native DXVK as unverified/unavailable for this recorded configuration. It must not infer support from a renderer candidate, shader cache, ICD file, or Vulkan loader presence. Recheck after a native driver/package change, then validate a real DXVK workload.

## NPU and AI workloads

Wine/Hangover does not automatically expose Android's NPU to a Windows application. Native NPU use is a separate integration project requiring a callable Android-side inference runtime, a documented app-to-runtime bridge, supported model operators and data types, and correctness/performance evidence. Ternuxx must show `not detected`, `not accessible`, `unsupported`, or `verified for named workload` as appropriate; it must not label an NPU active based only on the SoC model or an Android system service existing.

Android's NNAPI was deprecated in Android 15. Do not make it the default foundation for new NPU support. Any alternative must be checked for the device vendor, Android version, application context, distribution/licensing, and whether a Termux process can actually call it. A separate Android companion may be considered only with an explicit user-facing installation and permission model. Windows AI apps remain CPU-only unless their own runtime can use a verified backend or Ternuxx provides a proven bridge.

## Ternuxx management contract

The future software catalog and CLI/GUI manager should show runtime build/version, package source, executable architecture, prefix, display, graphics backend, and confidence level. Model Wine prefixes by app or profile; disclose storage and back them up before destructive changes. Prefix deletion, reset, registry edits, DLL overrides, and package removal require an exact preview and confirmation. Keep user data when removing runtime packages unless the owner separately selects prefix cleanup.

No Ternuxx Wine commands or management API operations currently exist. Do not infer install, launch, prefix, or recovery support from this research page.

Any future GUI should call the same validated manager operations as the CLI. It should report the selected runtime and backend and the actual outcome; it must not invent a successful launch from a spawned process alone.

## Fallback and acceptance

If the native runtime package or a required emulator component is absent, show the missing dependency and leave installation under the normal transaction preview. If a Windows app is unsupported, report the unsupported application and, where appropriate, point to a native Linux alternative; do not route the workload to another runtime. If GPU acceleration fails, say which path failed and use CPU only when the app supports that fallback and the user accepts it.

A compatibility entry becomes supported only after a named application and version is tested on the target device with its architecture, install steps, display, input, audio, CPU/GPU backend, correctness, memory, and sustained thermal behavior recorded. NPU claims require a named model/runtime and proof that inference actually ran on the NPU.

## Evidence and sources

- [WineHQ documentation](https://www.winehq.org/documentation) — Windows API compatibility-layer documentation.
- [Hangover upstream documentation](https://github.com/AndreRH/hangover) — architecture, emulator choices, package notes, and DXVK Vulkan requirements.
- [Termux package report: x86/x86-64 launch issue](https://github.com/termux/termux-packages/issues/27663) and [package update build issue](https://github.com/termux/termux-packages/issues/29816) — version-specific maintainer/user reports; treat as risk signals, not as device compatibility evidence.
- [Official Termux X11 package source tree](https://github.com/termux/termux-packages/tree/master/x11-packages) plus the device's local signed apt index — candidate availability was checked read-only on 2026-10-17; it is a dated snapshot and must be refreshed before planning an install.
- [Android NNAPI migration guide](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide) — NNAPI deprecation and Android ML migration context.

Research snapshot reviewed 2026-10-17. Package availability is dated; application compatibility, native Wine rendering, native DXVK, and NPU access are not verified. This document does not authorize a package transaction.
