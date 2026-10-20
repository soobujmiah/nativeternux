# Repository and reproducibility audit — 2026-10-20

Phase: `P3` (in progress; P4 remains planned)

## Repository integrity

- Native Termux checkout: `$HOME/ternuxx`, branch `main`, HEAD `0ecaac7746583d63856fbe95129a4ac92434245b`; it matched `origin/main` and had no dirty or untracked files at audit start.
- Source checkout uses `./tx`; installed `$PREFIX/bin/tx` dispatches to this checkout. No package, service, boot, GUI, or PRoot mutation was performed.
- Audit used owner-started Native Termux SSH 8022. An initial shell was Debian PRoot and correctly refused Native-only graphics/setup operations; live Native claims came from 8022.

## Live Native and PRoot observations

- `tx gui status --json`: native `:1` supervisor, X11, and XFCE live; Android GUI visibility is `unknown`.
- `tx graphics native status --json`: OpenGL renderer `Adreno (TM) 825`, `accelerated=true`, `verified`; Vulkan device `Adreno (TM) 825` is enumerated, with no draw verified.
- `tx info`: renderer is `unknown` in the SSH context because no display is selected. Use provider-specific graphics status/workload evidence for acceleration claims.
- `tx proot setup status --json`: saved profile `ternuxx-debian-trixie-workstation` is `profile_changed` against manifest `ba040d865c2078c5f58298f8e50ce2bb01d8d69eae568aa07a96b8f002d114cf`. This is profile drift; it does not mean the guest was updated to match.
- `tx pgui status`: managed standalone `:0` route is stopped and nested `:2` socket is absent. This does not inventory unrelated/unmanaged PRoot sessions.
- `tx virgl status --json`: stale recorded state; the exact recorded process is absent. No signal/cleanup was attempted.
- `tx mng cron status --json`: scheduler stopped, no jobs/executions, boot delivery not qualified, recovery delivery not installed.
- `tx mng boot cron status --json`: Termux:Boot app installed/enabled, but Cron integration script is missing and actual boot delivery is unverified.
- Native OpenGL and Debian Zink/Turnip evidence are separate provider results. Native Vulkan drawing, VirGL guest rendering, and fresh Debian replay are not verified.

## Repository-to-device reproducibility

| Area | Audit result | Reproducibility |
|---|---|---|
| CLI | Source `scripts/tx-installed` and installed `tx` dispatch track the checkout. | Reproducible from this checkout on configured Termux; requires Native runtime and dependencies. |
| GTK Management Center | Installed GTK binary/source/launcher identity matched the checked-out source and launcher identity in the live source audit. Repository installer rebuilds it. | Rebuildable with GTK build dependencies; no self-contained binary release. |
| TUI/Web | Runtime client source and assets are served from checkout. | Reproducible from checkout; tied to checkout path. |
| Native base packages | Preview/apply records the exact per-transaction closure, but resolves it from current signed indexes. | A future clean install is not guaranteed to get the same historical dependency versions. |
| Native accelerated graphics | Device-private experimental candidate is active and OpenGL status/workload is verified. Config says installer not implemented; no distributable artifact URL is pinned. | Not reproducible on clean install. Stock Mesa is clean-install baseline; Vulkan draw unverified. |
| Existing Debian PRoot | Versioned profile exists; package/config replay, fresh rootfs provisioning, backup/rollback migration, and managed reconciliation are incomplete. Adoption reports `profile_changed`. | Existing device setup is not reproducible from repository alone. No Bionic library is copied into Debian glibc paths. |
| Termux:Boot | Repository has service, recovery, and Cron scripts. Installed `00-ternuxx-services` and `ternuxx-recovery` differ by SHA-256; installed `10-ternuxx-profile` has no matching source file; installed `20-ternuxx-cron` is missing. | Device boot setup is not source-aligned; delivery is unqualified. |
| VirGL | Stale state records an absent process; no verified guest workload. | Not a verified usable/reproducible backend. |

Boot script comparisons were read-only; nothing was redeployed. Private runtime state, credentials, and device-specific candidate binaries are not copied into the repository.

## Inconsistencies corrected

- Refreshed the current checkpoint so it no longer presents old HEAD, renderer, VirGL PID, or an absent untracked path. Historical checkpoint entries remain dated records.
- Corrected the shared catalog's Debian login description: one foreground login passed identity checks; other lifecycle/concurrency gates remain open.
- Updated current installation/operations command examples to the supported `tx` entrypoint.

## Next work, in order

1. Review saved Debian profile drift with an exact preview; adoption does not install packages/config. Implement previewed guest package/config replay and rollback against a preserved target, then verify a disposable fresh Debian guest.
2. Build a clean-install Native graphics provider path with a distributable, pinned artifact/source and integrity checks. Until then, keep clean installs on stock Mesa and current acceleration device-specific.
3. Reconcile boot scripts with source through the preview/apply path, determine whether the legacy installed profile still has an owner, configure Cron boot integration when selected, and qualify delivery through a controlled reboot gate.
4. Resolve stale VirGL only after process/socket/client ownership is proven; verify a real PRoot workload.
5. Complete P3 GUI/recovery concurrency and owner visual acceptance, then review the P3 exit gate before activating P4.
6. Run the full Native suite and repository knowledge/README bridge checks after these changes. Keep Native, Debian PRoot, and UI results separately reported.

## Validation after audit corrections

- Native `bash scripts/repo_test.sh`: 594 tests passed in 106.627 seconds.
- `python3 -m tools.repo_knowledge verify`: 0 findings.
- `python3 tools/doc_bridge.py check --strict --project-id ternuxx README.md`: passed.
- `git diff --check`: passed.
- Live Native GUI/graphics/PRoot/boot status was re-read only; no live session was restarted or modified.

P3 remains active. P4 remains planned; P6 graphics completion and release readiness are not claimed.
