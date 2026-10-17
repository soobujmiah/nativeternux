# Installation status

NativeTernux is in active development. Its `install` command now contains a preview-first package transaction and can mutate the Termux package environment when explicitly invoked with `--yes`; that path has not been run or qualified on this device. A native desktop start/stop implementation now exists in source, but has not been executed, tested, or qualified on the device. The Ternux PRoot adapter remains unimplemented. Do not treat these code paths as a supported installation release.

## Current repository state

- `nativeternux check`, `info`, `doctor`, and `help` are inspection/documentation commands.
- `nativeternux install` previews a constrained package transaction. Code inspection shows `nativeternux install --yes` will invoke APT to install the approved package set; it was not run in this session and is not device-qualified.
- `nativeternux start`, `stop`, `restart`, and `status` have an initial ownership-aware implementation in `lib/desktop.sh` and `lib/desktop-supervisor.sh`. It has not been runtime-tested or device-qualified; do not invoke start/stop under the current read-only device instruction.
- No package installation was run during this documentation/research session. Do not invoke `install --yes` without a current preview and explicit owner authorization for that device mutation.

## Requirements under evaluation

The native desktop package transaction currently includes Termux:X11 host and XFCE packages from official Termux repositories. The Android Termux:X11 app remains a separate requirement. The exact package set and dependency plan must be rechecked immediately before any authorized installation. Upstream Termux:X11 currently documents enabling `x11-repo`, installing its companion package, then installing XFCE; exact package names and commands must be checked again before release. See the [upstream Termux:X11 guide](https://github.com/termux/termux-x11).

The native Termux Turnip test on the inspected Adreno 825 failed with `VK_ERROR_INCOMPATIBLE_DRIVER` for the observed package version. Native GPU acceleration must not be promised for that configuration without a passing live renderer check. Existing Ternux's separately managed Debian PRoot has a documented Zink/Turnip route; see [PRoot GPU reuse](PROOT-GPU.md). NativeTernux does not yet control or reuse that session. Current official local package-index candidates and the read-only XFCE dependency simulations are recorded in [Research & Evidence](RESEARCH.md#12-native-termux-desktop-packages-and-host-integrations); their exact transaction must be previewed again before implementation installs anything.

## Before an installation flow is published

Before release, re-verify package metadata, retain preview and explicit consent, and validate startup, repeated operations, failure cleanup, and unrelated-session preservation in an authorized test environment. The flow must leave the existing Ternux launcher and Debian rootfs untouched. Current device operation remains read-only, so runtime validation is deferred.
