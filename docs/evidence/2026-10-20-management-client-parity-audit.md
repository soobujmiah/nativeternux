# Management client parity audit — 2026-10-20

Phase: `P3`

## Scope and source

Audited the Native Termux checkout over the owner-started SSH 8022 development
shell. Before edits, Native reported branch `main`, HEAD `204b561`, tracking
`origin/main`, and a clean worktree. The PRoot-hosted workspace could not run
Native commands directly, so live build/install and repository tests were run
through SSH 8022. No Debian guest command, desktop lifecycle, boot setting,
service lifecycle, or Android UI input was used for this audit.

The shared service currently registers 84 typed API-v1 operations; the current
catalog supplies 13 categories and 20 resources with common operation
descriptions.
The four interfaces do not have equal action coverage, and catalog support does
not grant a client permission or imply that client has an action flow.

## Findings and changes

- CLI root help grouped commands by task, but aliases were only described as
  accepted, not enumerated. It also repeated the `pgui` example, and detailed
  TUI help described an obsolete 1–5/l/o key scheme. Help now lists the actual
  short forms, points to detailed help, removes the duplicate example, and
  describes the current Web and TUI scopes and keys.
- TUI displayed history as `h`, while lowercase `h` was consumed by category
  navigation. History is now advertised as uppercase `H`; `h` remains the
  previous-category shortcut. Graphics action hints now include GLES and only
  offer Native backend selection for the Native graphics resource. The guided
  graphics prompt now includes the already-implemented Native `select` action.
- GTK resource details previously hid the catalog's supported operation list
  and used a single OpenGL verification control even though the bridge accepted
  OpenGL, GLES, and Vulkan. The bridge now includes supported operations in its
  typed catalog output; GTK distinguishes shared supported operations from the
  controls actually available in that window and offers a provider-aware
  OpenGL/GLES/Vulkan picker.
- Web already presented supported/planned operations and exposed scoped desktop,
  graphics, monitoring, and managed SSH 8023 actions, plus Cron status/job-list
  reads. Its scopes intentionally do not grant PRoot lifecycle, Cron mutation,
  timezone mutation, boot mutation, or backup/recovery writes. README and the
  capability matrix now state these boundaries explicitly.

## Interface reach at audit time

Later same-day changes are recorded in the follow-up evidence listed in the current capability matrix. Do not treat this dated audit snapshot as the latest interface inventory.


- **CLI:** broadest command interface; groups include Cron definitions and
  history, timezone, boot, PRoot session/shortcut operations, backup/recovery,
  graphics, and service management. The operation registry is larger than the
  set of ordinary user-facing commands.
- **TUI:** catalog browsing/search, live reads, confirmed Native desktop and
  managed SSH 8023 lifecycle, Native and Debian graphics verification, Native
  graphics selection, monitoring-policy configuration, named PRoot app launch,
  Cron saved-job listing, and recovery history/details.
- **Web:** catalog browsing/search/filter, supported/planned operation details,
  scoped desktop lifecycle, graphics status/verification/Native selection,
  monitoring policy, managed SSH 8023 preview/confirmation, and read-only Cron
  status/job listing and recovery history.
- **GTK:** catalog browsing/search, live inspection, desktop start/stop,
  graphics status/OpenGL/GLES/Vulkan verification and Native selection, managed
  SSH 8023 preview/confirmation, monitoring policy, Cron saved-job listing, and
  recovery history. It does not yet offer PRoot app/session actions, timezone
  configuration, Cron mutation/history, boot, backup/restore, or SSH deploy.

The complete operation-by-operation comparison and remaining gaps are in
[`CAPABILITY-MATRIX.md`](../architecture/CAPABILITY-MATRIX.md). No phase gate
was marked complete.

## Evidence

This is incremental P3 management evidence. It records source/client coverage
and verification only; it does not pass the P3 recovery, concurrency, visual,
or boot acceptance gates.

## Verification and device installation

On Native Termux through SSH 8022:

- `bash tests/test_cli_help.sh` — PASS.
- `python3 -m unittest discover -s tests -p test_terminal_ui.py` — 19/19 PASS.
- `python3 -m unittest discover -s tests -p test_management_desktop_bridge.py`
  — 12/12 PASS.
- `clang -O2 -Wall -Wextra -fsyntax-only apps/management-center/management-center.c $(pkg-config --cflags gtk4)` — PASS with GTK4 4.24.1.
- `bash scripts/repo_test.sh` — 582/582 PASS.
- `git diff --check` — PASS.
- `./tx mng center install` — PASS. The installer validated the existing
  identity before replacing the app. Its installed binary hash is
  `608576c83d400aa9e97c7bb8b4ebcd87ae70f04eea839653cf669eccb31df1ea`; the
  recorded source C and bridge hashes match the checkout files.

The GTK window was not opened for human visual review, no currently running
management window was restarted, and browser rendering/mobile viewport was not
visually measured. Native `:1`, the current Codex session, and SSH 8022 were
left undisturbed. Therefore keyboard usability, visual layout, and the newly
installed GTK controls remain pending owner-operated visual confirmation.

## Remaining work

The clients still do not provide full operation parity. Per-client omissions
are listed in the capability matrix. Keep Web scope narrow until each additional
mutation has its own authorization and confirmation review. Continue P3's
recovery/concurrency and boot gates; P4 remains planned. No repository commit or
push result is asserted by this evidence file.
