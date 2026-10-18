# Shared management and repository audit — 2026-10-18

## Result

P3 remains the active phase. The owner-approved shared-management direction is now implemented for the first PRoot GUI app/shortcut slice: provider-scoped operations serve CLI, generated desktop entries, and the X11 shortcut manager. The local API remains read-only; there is no Web client, general X11 management client, or browser-friendly session bootstrap. A read-only management catalog and Doctor operation now enter the same service. Broader adapters and client surfaces remain incomplete; P3 remains active.

## Repository and worktree

- Checkout: `/data/data/com.termux/files/home/ternuxx`, branch `main`, HEAD `1a891fa`, configured origin `https://github.com/soobujmiah/ternuxx.git`. Local branch reports same commit as `origin/main`; no fetch was performed during this audit.
- Worktree contains 43 modified tracked paths and 317 untracked files (360 total paths with `git status --short --untracked-files=all`); nothing is staged. All 329 paths from the 09:36 audit remain present; 28 additional paths have appeared since that baseline, including the new shared PRoot shortcut service, schema, and fixture tests. Existing work was preserved.
- The worktree is too dirty to use `git status`'s default collapsed untracked-directory count as a complete file count. Use `--untracked-files=all` for future comparisons.
- `.repo/STATUS.md` remains a committed-state snapshot dated 2026-10-17. It is not evidence for the current uncommitted worktree or current device state.

## Phase and device state

- `project/phase-state.json` and generated phase docs identify P3 as `in_progress`; P4 remains planned behind P3 ownership and provider contracts.
- Native live status reports supervisor, X11, and XFCE running on `:1`; `gui_visible` remains machine-reported `unknown`. The owner confirmed seeing PRoot `xmessage` and later a PRoot Thunar window on that native display. This proves app-level X11 sharing, not PRoot desktop ownership or cold-boot recovery.
- Current read-only Doctor result is `warning`, with 14 pass, 15 info, 1 warning, and 0 errors. The warning is native SSH 8022 configured wildcard/password-enabled; listener ownership and external reachability remain unknown. Managed 8023 is a distinct loopback Runit service.
- The P3 exit-gate report has been refreshed with later `:1` recovery, Android activity retry, owner-confirmed PRoot windows, and the latest source-suite count. Device-only cold-boot and Shizuku gates remain open. P3 still has partial/open boot/GUI visibility and Shizuku gates; one visible PRoot app does not close those gates.

## Source, docs, and verification findings

- `docs/architecture/decisions/ADR-0004-three-interfaces-shared-management.md` now records the owner-approved shared-management requirement. `docs/ARCHITECTURE.md` and the header of `docs/architecture/UNIFIED-WORKSTATION.md` were aligned to distinguish accepted direction from incomplete implementation.
- The five-line installed-interface recheck was incorrectly named as a second ADR-0006. It has been moved to `docs/evidence/2026-10-18-p4-installed-ternux-interface-recheck.md` and added to P4 evidence; the actual provider decision remains `ADR-0006-adapt-existing-ternux-provider.md`.
- The final native Termux run passed 293/293 after the shared PRoot app/shortcut slice and mutation-classification tests were added. These source/fixture checks do not close P3 device gates or qualify a separate 8023 run.
- The follow-up repository checks are recorded below after completion; they do not replace P3 device gate review. New checks include catalog/Doctor service dispatch, strict catalog-schema parsing, phase refresh, repo-knowledge verification, and doc bridge validation.

## Next serial work

1. Finish the shared same-origin Web/X11 read-only client and browser session bootstrap; HTTP mutations remain disabled.
2. Adapt and verify the already-installed Debian PRoot from the shared service before enabling any guest lifecycle changes.
3. Implement selective distro (Debian/Ubuntu/other supported image) and desktop-environment install/remove only as preview-confirm/apply operations with ownership checks and recovery; XFCE4 is one selectable option, not a hard-coded only choice.
4. Add-on/plugin/tool adapters and cloud API provider remain planned; cloud network access stays disabled and credentials stay outside the catalog.
5. Continue remaining P3 native boot/SSH ownership, GUI visibility, and Shizuku gates; do not infer phase completion from catalog coverage.


## Follow-up repair and verification

- Full native suite: 295/295 passed via `bash scripts/repo_test.sh` over SSH 8022.
- The duplicate ADR filename was corrected by moving the five-line installed-interface note into P4 evidence and linking it from `project/phase-state.json`; no evidence was discarded.
- Owner-confirmed PRoot `xmessage` and Thunar windows on native `:1` establish app-level display sharing. They do not qualify cold boot, guest desktop ownership, or GUI visibility reporting.
- Final pre-commit worktree inventory: 43 modified tracked paths and 317 untracked files (360 paths total); nothing was staged before the reviewed change set.


## Shared PRoot GUI operation slice — 2026-10-18

- Added typed provider-aware operations `proot.app.launch`, `proot.shortcuts.list`, `proot.shortcuts.preview`, and `proot.shortcuts.apply` to the shared service, with exact capability mapping and [`proot-x11-shortcuts.schema.json`](../../schemas/proot-x11-shortcuts.schema.json).
- CLI shortcut administration, generated menu entries, and the X11 shortcut manager now route through the same service. Menu updates use a state-bound plan ID, explicit confirmation, atomic file replacement, and exact ownership checks. Guest user resolution reads the installed Ternux private state in-process; the value is not returned or logged.
- Live read-only service listing succeeded over native SSH 8022. Customized/unrecognized Terminal and Files entries were reported as conflicts and preserved; the exact legacy shortcut-manager entry was recognized. No menu file, running app, GUI service, or boot setting was changed during this audit.
- The owner previously confirmed Thunar was visible on native `:1`. This remains app-level X11 evidence only. Updated GUI manager interaction is pending; Web client/session bootstrap and HTTP mutation remain incomplete.


## Shared domain registry expansion — 2026-10-18

- Added read-only `management.catalog` and `doctor.report` operations to the typed shared service, exact `diagnostics.read` authorization, CLI commands, read-only HTTP classification, and [`management-catalog.schema.json`](../../schemas/management-catalog.schema.json).
- The catalog enumerates SSH/Runit servers, native and PRoot runtime, Doctor, autoboot/background, recovery, add-on/plugin/tool and API backend domains. It distinguishes active, partial, and planned support.
- PRoot lifecycle scope is planned in order: adapt installed Debian first; later selective distro install/removal (Ubuntu and other supported images) and selective desktop environments including XFCE4 and alternatives. No distro or package lifecycle action was run.
- Cloud API is a disabled provider placeholder: no outbound calls or credentials are accepted/stored. Add-on/plugin operations are also catalogued as planned where no adapter exists.
- Full suite: 295/295 passed. Targeted catalog tests: 2/2 passed. Live catalog and read-only Doctor service calls returned valid JSON. Doctor reported `error` in the remote environment; this is device health output, not a service dispatch failure. Repository knowledge verify: 0 findings; strict doc bridge passed; phase docs regenerated; `git diff --check` clean.
