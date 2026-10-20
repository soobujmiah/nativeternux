# Ternuxx-owned Debian PRoot consolidation — 2026-10-20

Phase: `P4` (preparatory work; phase remains planned)

## Evidence

## Read-only baseline

- Native runtime: Android 16, aarch64, Termux; repository checkout $HOME/ternuxx.
- Existing guest: $PREFIX/var/lib/proot-distro/containers/debian/rootfs, Debian 13 Trixie; it remains in place. No guest file, package, service, user, or process was changed for this audit.
- tx mng graphics status debian entered the guest through the fixed read-only verifier and reported zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)), X11 reachable, PulseAudio control endpoint reachable. This is the current Ternuxx runtime evidence.
- The installed Ternux CLI reports v1.4.0, configured user sbj, locale en_US.UTF-8, backend zink, and reports Turnip missing. The guest companion also reports v1.4.0. Ternux state is not a Ternuxx dependency and is not copied into this repository.
- The guest has 57 manually installed packages, including XFCE, graphics, fonts, development tools, and desktop applications. The new profile separates required desktop packages from optional workload groups.
- The active Debian Freedreno library is /usr/local/lib/aarch64-linux-gnu/libvulkan_freedreno.so, SHA-256 7ece28e1132cf791b6c81d4060142ff1481a239349fa86d7556c0883184caa5d. The active ICD config is /usr/local/share/vulkan/icd.d/ternux_freedreno_icd.json; it points to that library. This explains the old Ternux verifier's false negative: it checks /usr/lib/... and /usr/share/..., not the live /usr/local/... pair.
- The Trixie artifact URL and archive SHA-256 are recorded in Ternux's local installer state and were independently matched by downloading the release archive into the private Ternuxx cache. Archive SHA-256: c014cf66bdbff96417ee30d34f006cf51df64ae04893d599711b0b6b73b52ccf. The archive's packaged ICD hash is c9682812b58deb347fdeaa0fb3e5975651e20d37d31c682b2e5a7ed76ce348ae; the active /usr/local ICD is a separately rewritten file. The guest driver file hash matches the recorded release driver hash.
- The upstream release page lists the same archive checksum and release commit 98f3d6229d; the upstream project describes the standard package as supporting Adreno 8xx, including the 8xx route evaluated here. See the pinned release checksum and upstream project documentation.

## Ternuxx-owned setup

config/proot/debian-trixie.json is the first versioned setup contract. It does not contain private cookies, credentials, home paths, or per-device state. It records a Ternuxx-owned package profile, optional app groups, the pinned Turnip artifact, Zink launch variables, authenticated host audio handoff, and the rule that existing rootfs is adopted rather than replaced.

The repository still needs the executable staged installer, hash-bound adoption/config previews, config migration and rollback, and safe exact-file removal of the old Ternux CLIs. No Ternux CLI or PRoot mutation was performed. No GUI, SSH, PulseAudio, or Debian workload session was stopped.

## Adoption result

- `tx proot setup adopt-preview --user sbj` succeeded. The reviewed plan identified Debian 13 Trixie, the existing rootfs device/inode, the selected ordinary guest account, and both observed Turnip files; the operation listed no guest, package, or service changes.
- The confirmed adoption wrote the Ternuxx private provider record only (`guest_mutations=false`). A subsequent status reports `adopted` and no Ternux CLI dependency. No existing guest files, package state, services, running GUI, SSH, or Termux session were changed or stopped.
- This is only an existing-rootfs ownership record. It does not yet install packages, migrate guest configuration, reproduce the profile on a fresh install, or qualify legacy CLI removal.


- Unit coverage now exercises adoption preview/apply without guest writes, confirmation and stale-manifest rejection, Debian/user validation, and rootfs symlink rejection. The full suite passed 572/572.
