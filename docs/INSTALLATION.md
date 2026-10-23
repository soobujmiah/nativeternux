# Installation and upgrade guide

Ternuxx installs its Native Termux workstation packages through a saved, preview-first transaction. The Native install does not create or replace a Debian rootfs. A Debian guest is a separate, explicitly selected setup path.

## Quick install

On a fresh Termux profile, enable the Termux X11 package repository, install Git, clone Ternuxx, and preview the Native transaction:

```sh
pkg update && pkg install x11-repo git && pkg update
git clone https://github.com/soobujmiah/ternuxx.git "$HOME/ternuxx"
cd "$HOME/ternuxx"
./tx install --preview
```

Read the full package/dependency plan and exact preview ID. Apply only that saved plan:

```sh
./tx install --yes --plan-id PLAN_ID
```

The transaction refuses package removals and upgrades; this project does not yet provide a Native package upgrade/version-lock lifecycle. It does not promise the same repository candidate versions across dates; see [Native package-version drift](evidence/2026-10-23-native-package-version-drift.md). Install the matching Termux:X11 Android app separately for a desktop.

## First checks and desktop

```sh
./tx doctor
./tx info
./tx help
```

Open the Termux:X11 Android app, then start the Native desktop:

```sh
./tx start
```

For management, run `./tx tui`, `./tx web`, or `./tx mng center`. Their supported actions differ; see the [capability matrix](architecture/CAPABILITY-MATRIX.md).

## Choose a Debian path

- For a Debian Trixie guest you already use, inspect it and optionally create a Native-side adoption record. Adoption does not change guest files.
- For a new guest beside an existing Debian installation, use a unique `ternuxx-replay-NAME` alias and the fresh-install flow below. The target is isolated from the default `debian` alias.
- General package/config migration of an existing guest is not complete. Any authorized guest change must show its exact target/effects, preserve prior data, require explicit apply, and have a tested rollback.

The details, verification commands, and failure recovery steps follow.

## Current repository state

- `tx check`, `info`, `doctor`, and `help` are inspection/documentation commands.
- `tx install` previews the complete constrained APT transaction, including dependencies. The preview is recorded under `install-transactions/`; `--yes --plan-id ID` rebuilds the package closure and applies only when it exactly matches the private saved preview identified by ID, then asks APT for the full version-pinned package closure; success writes an `applied` record. If APT fails partway, some packages may already be installed; Ternuxx does not automatically remove them. Inspect APT output/history, then review a fresh preview before retrying.
- `tx start`, `stop`, `restart`, and `status` have an ownership-aware implementation in `lib/desktop.sh` and `lib/desktop-supervisor.sh`. The attached Android 16 / aarch64 target has completed start, repeated start, injected startup failure, stop, repeated stop, and preservation checks for the active PRoot login; the owner confirmed the `:1` desktop was visible and heard the audio test. These observations qualify only the recorded target and do not certify other builds. P2's acceptance gate is completed with a new target-native exact-preview validation; the original XFCE pre-consent console capture remains explicitly incomplete. See the [P2 completion evidence](evidence/P2-phase-completion-2026-10-18.md).
- Device package installation remains an explicit, owner-authorized mutation. Run `tx install --preview`, review the full saved transaction and its plan ID, then apply only that unchanged plan with `tx install --yes --plan-id ID`.

## Existing Debian provider

`tx proot setup status` reports whether the installed Debian rootfs is recorded by Ternuxx. A `profile_changed` result means the setup manifest differs from the saved Native adoption record; it does not prove guest drift and performs no repair. Compare the recorded and current hashes before choosing any adoption action; status never changes the guest or its adoption record. For an existing Debian Trixie rootfs, preview adoption with `tx proot setup adopt-preview --user NAME`, check the account, release, rootfs identity, and plan ID, then apply only that preview with `tx proot setup adopt --user NAME --yes --plan-id ID`. Adoption writes a private Native Ternuxx state record; it does not write to the guest.

This adoption step records the guest in private Native Ternuxx state. It does not install packages, migrate guest configuration, or retire files inside the guest. Legacy host/guest CLI targets are reviewed separately with exact previews and reversible operations; see [legacy CLI inspection](evidence/2026-10-23-legacy-cli-absence.md). A separate fresh Trixie installer supports a uniquely named disposable target beside the working Debian guest. The 2026-10-23 replay installed the pinned image/snapshot and verified its selected packages and account; it is not a clean-device, custom-workstation, GPU-rendering, or audio acceptance claim. See [fresh replay evidence](evidence/2026-10-23-disposable-debian-replay.md). General existing-guest package/config migration remains unfinished.

## Fresh Debian Trixie setup

On a clean Termux profile use the default `debian` target only when absent. To test alongside an existing guest, select an unused `ternuxx-replay-NAME` alias explicitly:

```sh
./tx proot setup fresh-preview --user NAME --alias ternuxx-replay-example
```

Check the selected user, dated Debian image and APT snapshot, package groups, available storage, and Turnip decision. Apply only the exact returned plan ID:

```sh
./tx proot setup fresh-install --user NAME --alias ternuxx-replay-example --yes --plan-id PLAN_ID
```

The installer checks the pulled arm64 image content before guest configuration. It uses the repository-pinned Debian image content and dated APT snapshot, provisions the selected manifest package groups, then verifies that every requested package is installed in the recorded dpkg inventory. The exact installed package versions are saved for that run. Arbitrary aliases, occupied containers and symlinked destinations are refused. The working `debian` rootfs is not overwritten. A refused target does not gain ownership through a failure journal. Package-stage retry can reuse the same failed preview and verified container/rootfs device/inode identity. If only the HTTPS mirror changes while the Debian snapshot, image, package profile and graphics decision remain compatible, create a new resume preview from the exact failed plan:

```sh
./tx proot setup fresh-resume-preview --user NAME --alias ternuxx-replay-example --plan-id FAILED_PLAN_ID
./tx proot setup fresh-install --user NAME --alias ternuxx-replay-example --yes --plan-id RESUME_PLAN_ID
```

The HTTPS bootstrap records the Native Termux CA bundle hash in the preview, stages that bundle temporarily in the guest, keeps Debian Release signature verification enabled, and removes the temporary copy when the guest setup shell exits, including package-stage failures. Fresh PRoot previews select groups with `--groups base,fonts`; `base` is required and omission selects the full manifest. The current Native preview avoids upgrades and detects a transaction, but it is not a permanent cross-date package-version lock; the Native version-lock/update lifecycle remains open. Existing Debian adoption remains available as a separate path. The Native core package set is fixed; optional Native workload selection and Web/TUI/GTK setup flows are open. Clean-device, rollback, and post-install rendering acceptance are not claimed.

See [the 2026-10-23 disposable replay](evidence/2026-10-23-disposable-debian-replay.md), [completed setup and scoped live acceptance](evidence/2026-10-22-fresh-setup-and-probe-safety.md), [earlier guarded replay evidence](evidence/2026-10-22-guarded-fresh-replay.md) and the [earlier fixture snapshot](evidence/2026-10-20-proot-fresh-reproducibility.md).

## Timezone default and selection

A new Ternuxx installation uses `Asia/Dhaka` by default. The preference is selectable after installation with `tx mng timezone set IANA_NAME`; `tx mng timezone status` and `list` inspect the resolved setting and available IANA names. A deployment may supply `TERNUXX_INSTALL_TIMEZONE` as an explicit installation preference. A saved owner selection takes precedence. Timezone support uses the installed Android/Termux database when available and does not install packages or call an external geolocation service. Optional IP-based suggestions are not implemented.

## Requirements under evaluation

### Planned shell selection (not implemented)

The future installer must let the owner choose Bash, Zsh, or Fish separately for Native Termux and the Debian PRoot provider. The currently active shell is a preselection hint only; the installer must not silently switch shells. Missing shell packages must appear in a provider-specific plan and require explicit confirmation before installation. Shell theme and configuration selection belongs to the shared management service and Ternuxx-owned overlays. No existing startup file or Ternux configuration is overwritten. See [ADR-0008](architecture/decisions/ADR-0008-shell-profiles-and-managed-configuration.md) and the [shell profile schema](../schemas/shell-profile.schema.json).

The Native workstation transaction includes `proot-distro`, Termux:X11, PulseAudio/D-Bus, Python, XFCE host packages, and the `glmark2`, `xorg-server-xvfb`, and `xdotool` graphics/X11 utilities. These support benchmarking, virtual X displays, and X11 input automation. The Native transaction does not create or replace a Debian rootfs. The existing Debian adapter supports inventory, a private read-only adoption record and explicit bounded guest verification. Verification login can write its generated profile; see [probe boundaries](PROOT-GPU.md). A separate preview-bound fresh Debian Trixie provisioner supports a distinct disposable alias and refuses occupied containers; live replay and clean-device acceptance are tracked above. Package/config migration of the existing guest is not implemented. Mesa, Turnip/Vulkan, and VirGL remain separate acceleration providers and are not installed by the base transaction. The Android Termux:X11 app remains a separate requirement. The exact package set and dependency plan are resolved from current signed indexes and rechecked immediately before any authorized installation; transitive packages are recorded per transaction rather than pinned as permanent direct installer targets. Package names and repository commands are release-sensitive; check the enabled signed Termux indexes and matching Android app before publishing a setup recipe.

### Planned optional software selection (not implemented)

The installer must offer optional software separately for **Native Termux** and **the selected Debian PRoot provider**. A user can select several named bundles or individual catalog entries for either side, or choose core-only. The same provider-scoped selection and preview service must later be used by CLI, Web Visualizer, and X11 GUI. See [ADR-0009](architecture/decisions/ADR-0009-provider-scoped-optional-software.md) and the [optional software catalog schema](../schemas/optional-software-catalog.schema.json).

The future interactive installer should present two independent multi-select lists and then one review screen grouped by provider. A future noninteractive CLI could expose explicit provider flags such as `--with-native <catalog-id,...>` and `--with-proot <catalog-id,...>`; these names are proposals, not current commands. If a selected shell is missing, its package requirement should appear in the same provider's preview, separately labeled as a shell prerequisite rather than an optional workload. Installing the same package in both providers requires selecting it on both sides.

Historical research inspected the separate Ternux installer as a behavioral reference: its live installer accepts `--with-dev`, `--with-llm`, `--with-network`, `--with-media`, `--with-blender`, and `--all`; the corresponding optional-workload phase runs Debian package operations inside `proot-distro login debian`. This verifies a PRoot-side named-workload selection pattern. It does not verify a two-provider selector in Ternux, nor does it establish that any of those package bundles are appropriate for native Termux. Ternuxx defines and verifies its own provider-specific catalog; no code was copied, and the Ternux CLI is not an installation or runtime dependency. [Ternux installer](https://github.com/soobujmiah/ternux/blob/main/install.sh), [optional workload phase](https://github.com/soobujmiah/ternux/blob/main/lib/phases.sh).

Safety and fallback requirements:

- Native selections resolve only through the Native Termux package adapter; PRoot selections only through the explicitly selected guest adapter. Do not silently retry the same package in the other provider.
- Non-interactive installation defaults to core-only. Explicit optional selections are required even with `--yes`; `--all` must be provider-scoped and show a preview.
- Show the provider, repository, package IDs, dependency changes, and reliable size data before confirmation. Unknown package sizes remain unknown.
- Cancellation, invalid catalog IDs, or an unavailable provider make no optional package changes. A failed optional item must be reported as failed; unrelated selections continue only if they are independent and partial completion can be reported safely.
- The existing Debian rootfs is never an implicit package target. The owner-selected existing Debian adapter is an explicit target; any guest package/config change must show its exact target and dependency plan and require explicit apply. Fresh provisioning targets a separately named, absent container; it does not migrate the existing guest.

This is a design requirement, not an implemented installer feature or device-qualified package list.

The historical Native Turnip test failed with `VK_ERROR_INCOMPATIBLE_DRIVER` for its recorded package version. Later API/workload evidence and remaining limits are tracked in [GPU qualification](testing/GPU-ACCELERATION.md); do not generalize one version/context to every backend. The existing Debian PRoot has a live-verified Ternuxx-managed Zink/Turnip route; see [PRoot GPU reuse](PROOT-GPU.md). The separate Ternux project is reference-only and its CLI is not required. Current official local package-index candidates and the read-only XFCE dependency simulations are recorded in [Research & Evidence](RESEARCH.md#12-native-termux-desktop-packages-and-host-integrations); their exact transaction must be previewed again before implementation installs anything.

## Before an installation flow is published

Before release, re-verify package metadata, retain preview and explicit consent, then validate fresh setup, startup/recovery, guest configuration rollback, existing workflow preservation, and old CLI removal on the target device. The 2026-10-23 disposable replay proves the pinned-image Debian package/setup path on the recorded Native Termux device only; it does not prove clean-device or complete Native-plus-PRoot workstation reproducibility. Do not replace the existing rootfs or broaden the replay result beyond its recorded scope.
