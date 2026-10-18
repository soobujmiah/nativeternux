# Software, distribution, and display catalog

I want the Ternuxx website to help me choose software and understand where it can run. It is a compatibility catalog and installation guide, not a remote installer. The local CLI remains responsible for inspecting the device and previewing package changes.

## What the catalog covers

Catalog entries may describe Termux-native command-line and graphical packages; applications in the existing Ternux Debian PRoot; Android companion applications and optional Termux integrations; Linux distributions and desktop/display combinations that passed their own support gates; and Native Wine/Hangover applications only after a named application has been tested.

Every entry identifies its execution provider. A package appearing in an index or a download link existing does not mean the application is supported on this device.

## User-facing support labels

| Label | Meaning | Website behavior |
|---|---|---|
| `research` | A source or compatibility path is being investigated | Explain open questions; do not present it as supported |
| `candidate` | A current official source/package candidate was found, but the workflow has not passed | Link to the official source and list what remains untested |
| `verified` | A named version passed documented install, launch, and workload checks in a named provider/device profile | Show evidence date, versions, limitations, and provider-specific install route |
| `limited` | A specific version works with a known restriction or fallback | State the restriction before the install link |
| `unavailable` | The tested configuration cannot currently provide the feature | Explain the tested failure and any explicit alternate provider |
| `stale` | Source or compatibility evidence is overdue or no longer resolves | Remove the supported action until reviewed |

Every label is scoped to version, ABI, Android/Termux range, provider, and review date. “Verified” never means every version or device works.

## Entry contract

Every published entry records:

| Field | Required information |
|---|---|
| Identity | Stable catalog ID, display name, upstream project, category |
| Source | Official project page, official download/package documentation, repository and package name where applicable |
| Provider | `termux-native`, `ternux-debian-proot`, `android-addon`, or a clearly named future provider |
| Compatibility | ABI, Android range if known, Termux/runtime version, libc or guest requirements, tested device profile |
| Desktop needs | Display backend, input, audio, fonts/locales, network or Android API requirements |
| Acceleration | CPU baseline and separately verified GPU/NPU backend, or `unverified` |
| Installation | Official upstream steps or a local CLI preview route; package source/version and dependency/space preview where available |
| Data and removal | User-data location, backup notes, removal scope, and whether data is retained |
| Evidence | Test date, exact versions, acceptance record, known issues, reviewer/source links |

Do not place credentials, user data, private keys, pairing material, or private device logs in catalog metadata. Use official HTTPS project or publisher pages. Prefer upstream signatures/checksums for downloadable artifacts and describe their verification status. Never tell visitors to paste opaque `curl | sh` commands.

## Provider and install flow

1. The user chooses an app and sees its support label, provider, compatibility notes, and official source.
2. The website offers official project instructions and, where implemented, a stable catalog ID for the local CLI.
3. The local CLI rechecks package availability and repository provenance at install time; website snapshots are informational only.
4. The CLI shows the exact provider, package source/version, dependencies, download/installed-size data where available, and affected paths.
5. The user reviews the transaction and explicitly confirms it. Failure records the package manager result and offers a targeted recovery path.
6. The CLI verifies installation and launch separately. It does not infer GPU acceleration or app compatibility from package installation.

Native Termux and Debian PRoot have separate package managers. The install target must be explicit; a missing package in one provider never triggers a silent install in the other. Optional apps remain outside the minimum desktop profile. Removing an optional app must not remove shared base components, user data, or any part of the existing Ternux rootfs.

### CLI experience

The premium CLI experience is a guided, inspectable flow, not decoration around an opaque command. The future catalog CLI should support search/list/detail and preview/install operations by stable app ID. The exact syntax remains an implementation decision; the contract is:

```text
ternuxx apps search <query>
ternuxx apps list [--category CATEGORY] [--provider PROVIDER]
ternuxx apps inspect <app-id>
ternuxx apps install <app-id> --preview
ternuxx apps install <app-id> --yes
```

`--yes` is explicit consent to the displayed transaction, not permission to widen its package set or provider. Interactive output should show numbered choices, current selections, package source, provider, dependencies/size when known, and the exact next action; support arrow-key selection when a suitable terminal is available and numbered/line input otherwise. It must remain readable without color, work over SSH, handle window resize, and expose the same facts in stable JSON for scripts. Progress output must distinguish download, package transaction, verification, and launch checks; errors include the failed step and a safe next command. Cancel exits without mutation. Avoid hiding long dependency output or asking the user to paste arbitrary shell fragments.

## Distribution compatibility matrix

The existing Ternux Debian guest is the first PRoot provider and remains independently owned. Ternuxx detects and reuses it; it does not reinstall, minimize, upgrade, or replace it. Other distributions remain proposals until a live official source and full install-to-workload path are reviewed.

| Provider/profile | Current classification | Requirements before promotion |
|---|---|---|
| Termux-native | Primary native provider | Package source/version, ABI, desktop/runtime dependencies, Android integration limits, and a device launch record |
| Existing Ternux Debian PRoot | Owner's established provider; integration is planned | Read-only identity/behavior check, exact launch environment, ownership-safe adapter, renderer/workload evidence, and parity check |
| Additional Debian-based PRoot profile | Candidate only | Separate identity/rootfs, supported bootstrap source, measured size, install/recovery/upgrade/removal tests on a disposable profile |
| Other PRoot distributions | Research only until individually qualified | Official bootstrap path, package lifecycle, architecture coverage, desktop/display/audio and accelerator test matrix |
| Chroot/container/rooted providers | Outside initial scope | Separate security, privilege, boot, backup, and root-management design; never imply PRoot provides kernel isolation |

Distribution selection must show rootfs identity, source, architecture, measured or source-qualified storage estimate, package manager, display/audio path, backup/removal boundary, and support label. No guessed “minimal rootfs” size is a supported estimate. Optional isolated profiles supplement the existing Ternux Debian and require a demonstrated workload gap.

### Distro research shortlist

The upstream [PRoot-Distro project](https://github.com/termux/proot-distro) currently documents OCI image based installation and names Debian, Ubuntu, Alpine, Arch, and openSUSE as examples. These are research candidates for a future catalog, not a promise that each image has a maintained Termux bootstrap, works on this device, or supports a desktop. Ternuxx must query the installed PRoot-Distro version and its actual image sources before offering any candidate. A distribution must pass the full compatibility and recovery gates above before its label can advance beyond `research`.

PRoot-Distro documents that nested PRoot is unsupported. Therefore any additional guest must be created and launched by the native Termux host, alongside the existing Ternux guest; Ternuxx must not attempt to launch a second PRoot instance from inside Ternux's Debian session. The existing Ternux rootfs remains separately owned and is not a disposable test profile.

## Display and desktop compatibility matrix

| Display path | Initial status | Promotion evidence |
|---|---|---|
| Termux:X11 | Initial native desktop target; upstream requires both Android app and Termux companion package | Exact app/package versions, server readiness, session launch, visible activity, input/resize, audio, repeat start/stop, failure rollback, unrelated-session preservation |
| Existing Ternux X11 session | Existing PRoot route is documented; current live behavior must be rechecked before Ternuxx claims control | Same-process renderer evidence, desktop behavior, display/audio ownership, and no regression to the current Ternux workflow |
| VNC | Candidate alternative, not a default fallback | Named server/client versions, authentication/bind security, latency/input, boot/recovery, and per-provider graphics evidence |
| Wayland compositor or nested Wayland | Research candidate | Exact provider package/compositor support, nested/native display constraints, input, clipboard, audio, GPU renderer, recovery |
| Other X servers or remote desktop clients | Catalog individually | Official source, security model, provider, device result, and interoperability contract |

The manager reports service readiness separately from whether Android visibly opened the display activity. VNC or Wayland cannot silently replace Termux:X11 after an error. Each profile names one desktop lifecycle owner per display. Display-server success does not establish that the application renderer is hardware accelerated.

## Minimum release checks

- Links resolve to the named official publisher/source and are reviewed for every release.
- Package candidate, repository, ABI, and version are refreshed at runtime before a transaction preview.
- Each verified app/distro/display claim links to dated evidence for the actual provider and device profile.
- Installer tests cover cancellation, dependency conflict, interrupted transaction, provider mismatch, and removal boundaries.
- Website catalog and CLI use the same stable IDs and support labels; the CLI remains authoritative for local state.
- Stale entries lose their supported action and remain only as clearly marked historical/research records where useful.
- No catalog claim promises generic GPU/NPU support, compatibility, performance, or fixed storage consumption.
