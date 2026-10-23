# Existing Debian profile state and graphics-path audit

Date: 2026-10-24 (Dhaka local)
Phase: P4, in progress

## Read-only package baseline

The current Debian rootfs identity was device 65086/inode 3240111. A bounded direct read of its `var/lib/dpkg/status` file counted both `install ok installed` and `hold ok installed`; this corrects an initial diagnostic parser that missed held packages. All requested manifest packages are already present: base 14/14, desktop compatibility 3/3, development 17/17, desktop apps 10/10, fonts 6/6. `libgl1-mesa-dri`, `mesa-vulkan-drivers`, `libegl-mesa0`, `libgbm1`, and `libglx-mesa0` are held at `25.0.7-2+deb13u1`. No upgrade was requested.

A root-only isolated `apt-get --simulate --no-install-recommends --no-upgrade --no-remove install libgl1-mesa-dri` returned 0 upgrades, 0 installs, 0 removals. It was not an apply. No guest package command was run afterward.

## Manifest graphics-path correction

`config/proot/debian-trixie.json` selects `/usr/local/lib/aarch64-linux-gnu/libvulkan_freedreno.so` and `/usr/local/share/vulkan/icd.d/ternuxx_freedreno_icd.json`. The existing guest has the driver at that exact path, with SHA-256 `7ece28e1132cf791b6c81d4060142ff1481a239349fa86d7556c0883184caa5d`, matching the pinned manifest driver. The selected ICD path is absent. The existing `/usr/local/share/vulkan/icd.d/ternux_freedreno_icd.json` is a different file; its JSON points to the same driver path, but that does not prove the loader selected it or that a workload rendered. Ternuxx adoption now reads the expected paths from the manifest, lists other ICD config names separately, and never calls another file the Ternuxx-managed ICD.

The existing adoption record carries a prior manifest hash that differs from the current manifest. The new preview binds that prior record and blocks apply instead of silently replacing it; a rollback-safe metadata refresh remains open. Current `./tx install debian preview` plan `521e1121f7d6ad5ec35402dca7bdc64e056b005de44e97fc9fa5ce6fa067c55c` reported 50/50 manifest packages installed, one held manifest package, exact Ternuxx ICD missing, and the other ICD filename. No apply was run. No guest file, package, service, process, account, or display was changed.

## Coverage and limits

Fixtures cover held-state parsing, architecture-qualified dpkg package names, package baseline drift, manifest-selected graphics paths, symlink refusal, and stale adoption-record preservation. These checks do not prove GPU acceleration or visible rendering. The migration for the legacy ICD config, guest package/config adaptation through shared clients, clean replay, and full rollback remain open.


## Final verification after profile-state implementation

The Native full suite passed 917 tests with 1 skipped in 108.135 seconds. Focused installer/presentation/CLI tests passed 19/19. The adoption preview now includes held-aware manifest group versions and package-state digest; status compares only manifest-selected packages. Tests cover installed/held states, multi-architecture package names, selected-package drift, manifest graphics path, symlink refusal, and preservation/blocking of an incompatible adoption record. `python3 -m tools.repo_knowledge verify` reported 0 findings; the document inventory had 0 broken links. No apply was run on the live guest or its prior adoption metadata.

## Credential creation boundary

Fresh Debian setup requires an explicit non-root username in the preview. During apply, the account is created if absent, added to the Debian sudo group, and assigned the newly confirmed password. The API now rejects an omitted password before invoking any guest operation. The secret is delivered to isolated guest chpasswd on stdin and is absent from argv and persisted setup records. Focused fresh-setup tests passed 19/19; the combined setup/adoption/CLI suite passed 38/38 after this change.

Native Termux keeps the app's existing Android/Termux identity and does not create a Linux user or sudo password. Existing Debian adoption resolves and records the guest account but does not create an account or change its password. Fresh account onboarding is currently implemented only for Debian Trixie; other proot-distro distributions and their distro-specific account/sudo setup remain unimplemented.


## Follow-up: rollback-safe metadata refresh

A subsequent change added private exact-byte backup and a separate exact rollback preview/apply for same-rootfs adoption metadata refresh. The 2026-10-24 full Native suite passed 922 tests with one skip in 145.509 seconds. The current Native record was refreshed through live preview 5639407fcb813a38a6d45678e8b850099a7353d0d78942d3b2758a023cdbb4c9; its old bytes are preserved under backup ID 0911df75f0a859bc0eec23d36d1dacdf5dab971a5fd64d55403f241f70d0e264. Status reports adopted, package baseline matches, and rootfs device/inode 65086/3240111. Rollback preview 550ba24b5c0b9810cde3572783844b37718d3278dcae79da1229bbd541983a0c succeeded but was not applied. No guest mutation occurred. Detailed evidence is in [adoption-record refresh evidence](2026-10-24-adoption-record-refresh.md).


## Follow-up: fresh installer now follows the manifest ICD path

A source audit found the fresh Debian helper used a legacy hard-coded ICD filename. It now validates and uses the manifest driver/ICD paths and refuses symlinks or conflicting files. The focused fresh setup suite passed 20/20. Read-only observations of existing replay aliases are recorded separately in [fresh Turnip path audit](2026-10-24-fresh-turnip-path-audit.md); no guest was changed.
