# Fresh Debian PRoot reproducibility — 2026-10-20

Phase: P4 (implementation slice; live clean-device install gate remains open)

## Implemented

- `tx proot setup fresh-preview --user NAME` plans a Debian Trixie install only when the ordinary `debian` alias is absent. It refuses to touch an existing rootfs.
- `tx proot setup fresh-install --user NAME --yes --plan-id ID` verifies the saved preview, manifest hash, plan body hash, private state paths, and per-plan lock before provisioning.
- The install uses the dated official image tag `debian:trixie-20261005` and explicitly selects `aarch64`. The repository records the official index digest plus the expected arm64 manifest, config, and layer digests. Installed PRoot-Distro 5.9 does not parse tag-plus-digest references, so after pull Ternuxx verifies the saved config/layer digests and image creation metadata before any APT or guest-user changes. A fixture test confirms a mismatched layer stops before the guest configuration command. PRoot-Distro also verifies the fetched arm64 manifest and all blobs against their registry digests.
- APT sources use the dated Debian and Debian Security snapshots `20261020T000000Z`. Signed Debian archive metadata remains required; `Check-Valid-Until` is disabled for the historical snapshot.
- Package groups, locale, ordinary user, and sudo group are installed from the repo manifest. The complete resulting dpkg package/version listing is stored privately with the setup record.
- When Native KGSL is accessible, setup fetches only the pinned Turnip archive and verifies its archive SHA-256 and both expected member SHA-256 values before copying the driver and ICD into the new guest. Mesa package holds are applied only in that fresh guest.
- A failed apply keeps its exact journal and may resume only with the same preview. An occupied or unowned rootfs is never adopted by the fresh installer.

## Live and fixture evidence

- On the current device, `tx proot setup fresh-preview --user sbj` refuses because the existing `debian` rootfs is present. No guest package, profile, service, process, or file was changed by this fresh-install check.
- The existing Debian adapter record was refreshed against the updated manifest using the read-only adoption preview plus Native-state-only apply. It now reports `adopted`; the rootfs device/inode identity did not change.
- After the full test suite, a read-only live check again showed the installed `debian` container and active PRoot login sessions, including standalone display `:0`. The Native desktop `:1` remained stopped. No PRoot session was signaled or changed. The adoption record had become `profile_changed` after the manifest edit, so the exact adoption preview was re-applied to Native private state only; it now reports `adopted` with rootfs device/inode `65086:3240111`, and the same `debian` container remains installed.
- The pinned archive was downloaded to private Native state and verified successfully: archive size 11,648,933 bytes, Turnip driver 17,483,184 bytes with the manifest SHA-256, and ICD member 198 bytes with the manifest SHA-256. This verifies artifact integrity, not a fresh guest render.
- Snapshot `InRelease` endpoints for `trixie`, `trixie-updates`, and `trixie-security` returned HTTP 200 from the device. The package transaction and source configuration are fixture-tested; the package manager has not been run in a fresh guest.
- Fixture tests cover private preview, exact plan validation, separate alias creation, existing-rootfs refusal, package inventory recording, and resume after an interrupted package step. Seven fresh-provisioning fixture tests pass, including a wrong-layer-digest rejection before package configuration; the full Native Termux repository suite passed 605/605. They do not substitute for a clean-device installation.

The official PRoot-Distro docs describe custom container names, explicit architectures, and digest-pinned OCI references, although this device's installed parser requires the dated tag plus post-pull content verification: [PRoot-Distro install documentation](https://github.com/termux/proot-distro/blob/master/README.md#install--install-a-container). The chosen Debian image digest is listed by the [official Debian image page](https://hub.docker.com/layers/library/debian/trixie-20261005/images/sha256-bcf83fd8af414eda0c0a99d25a4e61dedd88e7aac7f7bc519d04555ff0c40ec5). Debian documents dated archive URLs and disabling validity dates for old signed snapshots at [snapshot.debian.org](https://snapshot.debian.org/).

During a later status check, PRoot standalone display :0 was running and Native display :1 was stopped. I had not started or stopped either session during the provisioning work, so both were left untouched.

## Remaining gates

- Apply the installer on a genuinely clean Termux profile where `debian` does not exist, then verify XFCE startup and package inventory.
- Verify the new guest's Turnip/Vulkan and OpenGL rendering from actual workloads; package/file presence is not render proof.
- Add exact preview-bound rollback for a fresh-install alias and lifecycle-aware installer integration to the shared Web/TUI/GTK management surfaces.
- Native Vulkan draw, ordinary-workload API-aware fallback, NPU runtime, and device cold-boot delivery remain separate open tasks.
