# Disposable Debian Trixie replay — 2026-10-23

## Target and plan

- Native Termux repository: `$HOME/ternuxx`, branch `main`
- Fresh alias: `ternuxx-replay-audit-20261023`
- Guest user: `txaudit`
- Plan: `c27f37fc1a0bc3b5ae33db03f0f2eeb02c3be8d968bdcca9c2c063feeab18de7`
- Debian base image: pinned arm64 image in the Ternuxx manifest
- APT snapshot: `20261020T000000Z`; HTTPS Cloudflare snapshot mirror
- Package groups: all five manifest groups; 50 requested packages
- HTTPS bootstrap: hash-bound Native Termux CA bundle, temporary guest copy, Debian Release signatures retained

This resumed the exact failed package stage for this newly created disposable alias
after the mirror-only change. The resume preview retained the pinned image,
snapshot, package set, graphics choice, rootfs identity and idle-process guard.

## Result

The installer returned `status: installed`, recorded the exact package-version
inventory, and reported all requested packages verified. A separate read-only
check of the guest rootfs found:

- Debian Trixie release identity and the `txaudit` account;
- all 50 requested manifest packages installed;
- the temporary `/tmp/ternuxx-native-ca.pem` file removed;
- the manifest's KGSL plan placed `libgl1-mesa-dri` on hold;
- the pinned Turnip artifact installed, with `turnip_runtime_verified: false`.

The package stage fetched 759 MB from the dated signed snapshot. It did not target
the existing `debian` alias. A read-only `tx proot status` still listed both
`debian` and the replay alias, did not enter a guest, and observed the active
Codex PRoot PID 590.

## Scope

This qualifies the completed package/setup replay on this Native Termux device.
It does not qualify a clean-device install, visible XFCE/Firefox rendering,
Turnip/Vulkan runtime, audio, or another Android build. The default guest and
active Codex PRoot session remain outside the replay target.

See [the installer guide](../INSTALLATION.md) and `fresh setup implementation`.

## Evidence

Phase: `P4`

P4 fresh Debian Trixie setup replay on Native Termux. The installer and CLI are the implementation under review.

- `Setup implementation`
- `CLI routing`
- [Installation guide](../INSTALLATION.md)
