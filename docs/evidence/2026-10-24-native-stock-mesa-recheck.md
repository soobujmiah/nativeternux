# Native stock Mesa recheck — 2026-10-24

Phase: `P6`
**Evidence class:** direct Native Termux package inventory and bounded workload checks.
**Target:** Redmi `25053RT47C`, Android 16/API 36, aarch64, Termux `0.119.0-beta.3`.

## Evidence

### Result

I reran the shared graphics verifier against the installed Termux Mesa packages while giving it an empty private temporary state directory. This kept Ternuxx's saved experimental KGSL selection out of the probe. The temporary tree was removed after the run; no package, persistent selection, or live desktop/service changed.

| API | Current stock result | Evidence boundary |
|---|---|---|
| OpenGL | `llvmpipe (LLVM 21.1.8, 128 bits)`, off-screen draw passed, score 81 | CPU software rendering; this does not establish hardware acceleration |
| GLES | Runner unavailable, exit 127 | No context or draw was verified |
| Vulkan | No valid GPU detected; enumeration exit 1 | No draw was attempted |

The installed package versions were Mesa `26.2.5`, `mesa-vulkan-icd-freedreno` `26.2.4`, and `vulkan-loader-generic` `1.4.365`. The configured `termux-main` source was `https://termux.danyael.xyz/termux/termux-main`; the Freedreno ICD candidate was `26.2.5`. No package transaction was performed.

The [official Termux Mesa recipe](https://github.com/termux/termux-packages/blob/master/packages/mesa/build.sh) currently declares Mesa `26.2.5` and configures Gallium drivers `llvmpipe,softpipe,virgl,zink`. Its aarch64 build separately enables Freedreno Vulkan with `-Dfreedreno-kmds=msm,kgsl`; the [Freedreno subpackage recipe](https://github.com/termux/termux-packages/blob/master/packages/mesa/mesa-vulkan-icd-freedreno.subpackage.sh) packages the Vulkan ICD. Package configuration alone does not prove a workload draw.

The Adreno 825 OpenGL/GLES/Vulkan draws recorded in the [experimental graphics recheck](2026-10-24-native-graphics-fallback-recheck.md) came from a separate Mesa `26.3.0-devel` candidate. Its source remains a [community draft](https://github.com/lfdevs/termux-packages/pull/25), and it has no stable clean-install distribution route. Keep that candidate outside the release-supported graphics path. Current live `tx mng graphics status native` reports the saved candidate, an Adreno OpenGL renderer, GLES context, and Vulkan device enumeration; those status fields are not draw evidence.

Raw structured results: [native stock Mesa recheck JSON](data/2026-10-24-native-stock-mesa-recheck.json). This recheck does not validate other devices, a clean installation, application rendering, GPU inference, or NPU execution.
