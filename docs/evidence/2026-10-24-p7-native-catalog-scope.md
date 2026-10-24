# P7 Native catalog scope and package-source audit — 2026-10-24

Phase: `P7`
**Evidence class:** current Native Termux package metadata/simulation, official Termux package recipes, and repository source review.
**Scope decision:** start with three small official `termux-main` CLI utilities. The catalog must use stable Ternuxx app IDs and resolve exact package versions/dependencies from the current signed local Termux indexes at preview time; it must never bake observed versions into install requests.

## Evidence

The current management catalog is read-only: `management.catalog` returns resource metadata and operation capabilities. `lib/phases.sh` implements preview-first base-profile install and core-package update only. `docs/SOFTWARE-CATALOG.md` correctly states that per-app install/update/remove and shared client actions are not implemented. No app lifecycle operations exist in `lib/management_service.py`, and no package lifecycle controls exist in the TUI, authenticated Web UI, or GTK center.

A read-only local package-index inspection found these currently absent packages and exact candidates in the configured `termux-main` source. The simulation resolved all three direct packages plus `utf8proc`, with no upgrades or removals:

| App ID | Package | Local candidate snapshot | Purpose |
|---|---|---:|---|
| `process-monitor` | `htop` | `3.5.3` | Interactive process/resource monitor |
| `terminal-multiplexer` | `tmux` | `3.8` | Persistent terminal sessions |
| `directory-tree` | `tree` | `2.3.2` | Readable directory tree output |

Exact read-only result: `0 upgraded, 4 newly installed, 0 to remove`; dependency closure adds `utf8proc`. Each direct candidate's `apt-cache policy` source was `https://termux.danyael.xyz/termux/termux-main` (the configured `termux-main` mirror). No package was installed, removed, upgraded, or downloaded. `nano` was excluded because it is already installed on the observed device and the three selected tools provide distinct optional workflows.

The package index is a device snapshot, not a maintained catalog version. The read-only repository age gate returned fresh for the currently configured Termux indexes, and no index refresh occurred. These versions remain evidence only; every implemented preview must recheck index freshness and query the current candidate/source again. Install/apply must be blocked unless the exact candidate and every resolved dependency come from the official `termux-main` repository, the full APT simulation contains no removals or upgrades, and the user confirms the exact saved plan. Update is explicit and package-scoped. Remove must preview the exact selected package and refuse dependency/removal drift; it must never invoke autoremove.

Official package recipes reviewed: [htop](https://github.com/termux/termux-packages/blob/master/packages/htop/build.sh), [tmux](https://github.com/termux/termux-packages/blob/master/packages/tmux/build.sh), and [tree](https://github.com/termux/termux-packages/blob/master/packages/tree/build.sh). They are Native Termux packages maintained in the official `termux/termux-packages` repository; the recipes and runtime index supply provenance and current versions, while this Ternuxx catalog owns only the curated app IDs and supported lifecycle contract.

## Implementation status

This document records the pre-implementation scope snapshot. P7 lifecycle implementation and current validation are recorded in [the completion evidence](2026-10-24-p7-native-catalog-implementation.md).

## Original next implementation gate

Add a typed shared package lifecycle for these three IDs only: list/status, install/update/remove preview, exact plan confirmation, bounded package-manager execution, and recorded result. Keep arbitrary package names and external repositories out of the request contract. Then expose the same actions and preview summary in `tx`, TUI, Web, and GTK; test stale plans, mirror/dependency drift, cancellations, failures, removal scope, and identical authorization. Device apply remains unqualified until separately authorized and run through the exact preview.
