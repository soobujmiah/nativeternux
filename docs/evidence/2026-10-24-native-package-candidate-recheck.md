# Native package candidate recheck — 2026-10-24

## Target

- Canonical Native Termux checkout: `$HOME/ternuxx`, `main` at `b170fcee897a06981bc5e04f234d638c4ab8af2f` before this evidence update.
- Runtime: Native Termux over development SSH 8022; `PREFIX=/data/data/com.termux/files/usr`; APT package architecture `aarch64`.
- No index refresh or package change was performed.

## Index and candidate check

The existing local InRelease metadata reported:

- Termux main: `2026-10-22 16:31:15 UTC`
- Termux X11: `2026-10-22 13:36:48 UTC`

Read-only `apt-cache policy` showed 12 of the 16 direct Native workstation packages already at their current candidate. Three direct packages differ:

- `proot-distro`: installed `5.9.0`, candidate `5.10.2`
- `pulseaudio`: installed `17.0-4`, candidate `17.0-5`
- `python`: installed `3.14.6-1`, candidate `3.14.8`

The candidate set also includes a third-party TUR version for Python; Ternuxx's existing candidate selector accepts only the designated official Termux main/X11 sources. The read-only simulation was explicitly constrained to the three official main candidates:

```sh
apt-get -s --no-install-recommends --no-remove install \
  proot-distro=5.10.2 pulseaudio=17.0-5 python=3.14.8
```

APT resolved `python-ensurepip-wheels` as the fourth upgrade: **4 upgraded, 0 newly installed, 0 removed**. No upgrade was applied; Native and PRoot workloads remain untouched.

## Reproducibility boundary

The current installer records and reapplies a transaction only while its selected versions remain available. Termux describes its package ecosystem as a rolling release; maintainers have stated that legacy package versions are not supported or planned. Therefore a version manifest can detect drift and fail closed, but cannot alone guarantee that a future fresh install can retrieve an old `.deb`. A long-lived exact replay additionally needs controlled retention of the selected package artifacts and repository metadata. Ternuxx does not currently operate or qualify such a mirror/cache.

Sources:

- [Termux package management guidance](https://github.com/termux/termux-packages/wiki/Package-Management) recommends updating packages to currently available versions and describes mirror changes.
- [Termux package maintainers' discussion of legacy package versions](https://github.com/termux/termux-packages/discussions/20330) states the rolling-release and legacy-support boundary (discussion dated 2024-05-26).

## Limits and next work

This is a current-device candidate and solver recheck, not a clean-device install or proof that old package artifacts are unreachable from every mirror. Implement the explicit, preview-first update/lock lifecycle using the existing transaction model. Keep artifact retention and cross-date replay as a separate release limitation until a maintained, integrity-checked source is available.

## Evidence

Phase: `P4`

Read-only Native Termux APT policy and simulation; no package state changed.
