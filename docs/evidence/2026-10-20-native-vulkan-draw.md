# Native Vulkan draw verification — 2026-10-20

Phase: P6 implementation evidence; phase exit gate remains open.

## Result

The shared Native graphics verifier now performs a bounded Vulkan draw instead of stopping at physical-device enumeration. On the Adreno 825 device, `tx mng graphics verify native vulkan :1 --json` returned `status=rendered`, `render_verified=true`, `device=Adreno (TM) 825`, `draw_renderer=Adreno (TM) 825`, and `draw_frames=120`.

The verifier used the saved Ternuxx KGSL/Freedreno candidate environment and ran `vkcube --c 120` on Native X11 display `:1`. `vulkaninfo --summary` and the draw both exited 0, and the selected GPU string matched the enumerated Vulkan device. A direct invocation without the candidate environment selected the stock Turnip ICD and failed with `VK_ERROR_INCOMPATIBLE_DRIVER` for GPU id 6830. That result is retained as evidence about the stock route; it does not describe the candidate environment.

## Implementation and safety

- `graphics_manager.verify("native", "vulkan")` now checks enumeration, requires `vkcube` and an active display, bounds the test to 120 frames/20 seconds, and reports success only when the draw exits cleanly on the same named GPU.
- Missing display or test binary leaves the result at `enumerated`; an enumeration failure, draw failure, timeout, or device mismatch never reports a rendered workload.
- Three fixture tests cover matching-device success, renderer mismatch rejection, and enumeration-only behavior without a display.
- Focused graphics management tests passed 12/12. The shared CLI path returned the same successful 120-frame result.
- No package was installed; no graphics preference, desktop/service lifecycle, Debian rootfs, guest configuration, or unrelated process was changed. The bounded cube window closed after its frame limit; Native XFCE and the running PRoot sessions were left alone.

This verifies a Native Vulkan presentation workload on `:1` through the selected experimental candidate. It does not establish Vulkan inference, broad app compatibility, sustained performance/thermal behavior, clean-install driver reproduction, or the nested full-desktop `:2` presentation path. P6 remains open.
