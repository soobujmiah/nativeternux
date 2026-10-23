# Fresh Debian Turnip path audit

Date: 2026-10-24 (Dhaka local)
Phase: P4, in progress

## Finding and correction

The Debian Trixie manifest selects /usr/local/share/vulkan/icd.d/ternuxx_freedreno_icd.json and /usr/local/lib/aarch64-linux-gnu/libvulkan_freedreno.so. The fresh provisioning helper had hard-coded a legacy ICD filename and driver path, so its write targets could drift from the manifest that adoption and status inspect.

The helper now validates both manifest paths, uses them to set ICD library_path and write destinations, and checks existing destinations for symlinks or bytes that do not match the exact staged artifact. Existing conflicting files cause setup to fail instead of being overwritten. The helper still acts only on a Ternuxx-owned fresh setup target selected by the existing exact plan.

## Verification

A fixture uses non-default safe manifest paths and verifies both generated destinations, the corresponding ICD library path, refusal conditions, and shell syntax. The focused fresh setup suite passed 20/20 after this change. The full repository suite then passed 923 tests with 1 skipped in 103.996 seconds (exit code 0). No guest was entered or changed during this correction.

A read-only Native rootfs inventory found the current Ternuxx ICD filename in replay aliases ternuxx-replay-audit-20261023, ternuxx-replay-p4, ternuxx-replay-p4-coldboot, and ternuxx-replay-p4-retry, all with SHA-256 4b589776fa718e61e1d607b894f16134c0465802e39549d76c67e653d8c00c97 and the manifest driver path. ternuxx-replay-repro had neither inspected ICD filename. These observations do not identify which historical installer revision wrote the replay files and do not prove rendering or acceleration. No replay rootfs was changed.

This corrects source/manifest alignment but does not qualify a newly provisioned clean guest or close visible GUI, renderer, audio, existing-guest migration, or cross-client gates.
