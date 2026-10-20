# Installation status

Ternuxx is in active development. Its `install` command uses a saved, preview-first package transaction. Applying requires explicit `--yes` plus the plan ID printed by the reviewed preview; the current APT plan must still match that saved record. The approved 2026-10-18 XFCE install is recorded in [P2 transaction evidence](evidence/P2-termux-xfce-install-transaction-2026-10-18.json). New previews and successful applies persist their exact APT simulations and package/version closure under the private Ternuxx state directory. Native desktop start/stop has been exercised on-device; remaining phase gates are listed in the P2 evidence. Ternuxx now owns its Native-to-Debian PRoot display/audio/graphics handoff and does not require or invoke the separate Ternux CLI. The existing Debian userland remains preserved; full PRoot lifecycle and clean-install qualification remain open. Do not treat these code paths as a supported installation release.

## Current repository state

- `ternuxx check`, `info`, `doctor`, and `help` are inspection/documentation commands.
- `ternuxx install` previews the complete constrained APT transaction, including dependencies. The preview is recorded under `install-transactions/`; `--yes --plan-id ID` rebuilds the package closure and applies only when it exactly matches the private saved preview identified by ID, then asks APT for the full version-pinned package closure; success writes an `applied` record. If APT fails partway, some packages may already be installed; Ternuxx does not automatically remove them. Inspect APT output/history, then review a fresh preview before retrying.
- `ternuxx start`, `stop`, `restart`, and `status` have an ownership-aware implementation in `lib/desktop.sh` and `lib/desktop-supervisor.sh`. The attached Android 16 / aarch64 target has completed start, repeated start, injected startup failure, stop, repeated stop, and preservation checks for the active PRoot login; the owner confirmed the `:1` desktop was visible and heard the audio test. These observations qualify only the recorded target and do not certify other builds. P2's acceptance gate is completed with a new target-native exact-preview validation; the original XFCE pre-consent console capture remains explicitly incomplete. See the [P2 completion evidence](evidence/P2-phase-completion-2026-10-18.md).
- Device package installation remains an explicit, owner-authorized mutation. Run `ternuxx install --preview`, review the full saved transaction and its plan ID, then apply only that unchanged plan with `ternuxx install --yes --plan-id ID`.

## Timezone default and selection

A new Ternuxx installation uses `Asia/Dhaka` by default. The preference is selectable after installation with `tx mng timezone set IANA_NAME`; `tx mng timezone status` and `list` inspect the resolved setting and available IANA names. A deployment may supply `TERNUXX_INSTALL_TIMEZONE` as an explicit installation preference. A saved owner selection takes precedence. Timezone support uses the installed Android/Termux database when available and does not install packages or call an external geolocation service. Optional IP-based suggestions are not implemented.

## Requirements under evaluation

### Planned shell selection (not implemented)

The future installer must let the owner choose Bash, Zsh, or Fish separately for Native Termux and the Debian PRoot provider. The currently active shell is a preselection hint only; the installer must not silently switch shells. Missing shell packages must appear in a provider-specific plan and require explicit confirmation before installation. Shell theme and configuration selection belongs to the shared management service and Ternuxx-owned overlays. No existing startup file or Ternux configuration is overwritten. See [ADR-0008](architecture/decisions/ADR-0008-shell-profiles-and-managed-configuration.md) and the [shell profile schema](../schemas/shell-profile.schema.json).

The native desktop package transaction currently includes Termux:X11 host and XFCE packages from official Termux repositories. The Android Termux:X11 app remains a separate requirement. The exact package set and dependency plan are resolved from current signed indexes and rechecked immediately before any authorized installation; transitive packages are recorded per transaction rather than pinned as permanent direct installer targets. Upstream Termux:X11 currently documents enabling `x11-repo`, installing its companion package, then installing XFCE; exact package names and commands must be checked again before release. See the [upstream Termux:X11 guide](https://github.com/termux/termux-x11).

### Planned optional software selection (not implemented)

The installer must offer optional software separately for **Native Termux** and **the selected Debian PRoot provider**. A user can select several named bundles or individual catalog entries for either side, or choose core-only. The same provider-scoped selection and preview service must later be used by CLI, Web Visualizer, and X11 GUI. See [ADR-0009](architecture/decisions/ADR-0009-provider-scoped-optional-software.md) and the [optional software catalog schema](../schemas/optional-software-catalog.schema.json).

The future interactive installer should present two independent multi-select lists and then one review screen grouped by provider. A future noninteractive CLI could expose explicit provider flags such as `--with-native <catalog-id,...>` and `--with-proot <catalog-id,...>`; these names are proposals, not current commands. If a selected shell is missing, its package requirement should appear in the same provider's preview, separately labeled as a shell prerequisite rather than an optional workload. Installing the same package in both providers requires selecting it on both sides.

Historical research inspected the separate Ternux installer as a behavioral reference: its live installer accepts `--with-dev`, `--with-llm`, `--with-network`, `--with-media`, `--with-blender`, and `--all`; the corresponding optional-workload phase runs Debian package operations inside `proot-distro login debian`. This verifies a PRoot-side named-workload selection pattern. It does not verify a two-provider selector in Ternux, nor does it establish that any of those package bundles are appropriate for native Termux. Ternuxx defines and verifies its own provider-specific catalog; no code was copied, and the Ternux CLI is not an installation or runtime dependency. [Ternux installer](https://github.com/soobujmiah/ternux/blob/main/install.sh), [optional workload phase](https://github.com/soobujmiah/ternux/blob/main/lib/phases.sh).

Safety and fallback requirements:

- Native selections resolve only through the Native Termux package adapter; PRoot selections only through the explicitly selected guest adapter. Do not silently retry the same package in the other provider.
- Non-interactive installation defaults to core-only. Explicit optional selections are required even with `--yes`; `--all` must be provider-scoped and show a preview.
- Show the provider, repository, package IDs, dependency changes, and reliable size data before confirmation. Unknown package sizes remain unknown.
- Cancellation, invalid catalog IDs, or an unavailable provider make no optional package changes. A failed optional item must be reported as failed; unrelated selections continue only if they are independent and partial completion can be reported safely.
- The existing independent Ternux PRoot rootfs is never an implicit package target. Default PRoot install scope is a separately managed Ternuxx guest. Any future install adapter into the existing Ternux guest needs a distinct approved scope and exact-target preview.

This is a design requirement, not an implemented installer feature or device-qualified package list.

The native Termux Turnip test on the inspected Adreno 825 failed with `VK_ERROR_INCOMPATIBLE_DRIVER` for the observed package version. Native GPU acceleration must not be promised for that configuration without a passing live renderer check. The existing Debian PRoot has a live-verified Ternuxx-managed Zink/Turnip route; see [PRoot GPU reuse](PROOT-GPU.md). The separate Ternux project is reference-only and its CLI is not required. Current official local package-index candidates and the read-only XFCE dependency simulations are recorded in [Research & Evidence](RESEARCH.md#12-native-termux-desktop-packages-and-host-integrations); their exact transaction must be previewed again before implementation installs anything.

## Before an installation flow is published

Before release, re-verify package metadata, retain preview and explicit consent, and validate startup, repeated operations, failure cleanup, and unrelated-session preservation in an authorized test environment. The flow must leave the existing Ternux launcher and Debian rootfs untouched. The owner has allowed X11 testing, but device lifecycle validation remains blocked on missing native XFCE packages; do not install those packages without a separate package-change authorization.
