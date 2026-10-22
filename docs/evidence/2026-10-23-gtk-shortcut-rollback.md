# GTK PRoot shortcut rollback review

Date: 2026-10-23
Runtime: Native Termux, checkout `~/ternuxx` over SSH 8022

## Result

The GTK management center now exposes a **Restore saved PRoot app menu…** action for the Existing Debian PRoot resource. The visible review screenshot is [here](gtk-shortcut-rollback-visual.png). It confirms that the action appears in the resource action list at a 752×1124 capture size. This is layout evidence only; it does not prove the button callback completed.

The installed GTK identity record matches the current source and installed artifacts:

- C source SHA-256: `20eeaa02a400c0d581ea501ab0c0dd81420a3db30d53ec665b04b8a48c8e3f75`
- Desktop bridge SHA-256: `8333c9c3a39b680f3b18743293382dd7e35d9e5104acc65adf1af8b66bd93df2`
- Installed binary SHA-256: `cf5934301fe2623ccda39f9ac5602d8fefa067bccd2ce7633939b618529a7131`
- Installed launcher SHA-256: `e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd`
- Installed desktop entry SHA-256: `85136ed5cf3a658fc35ac8a6105abff6da07f6b2a775efa0bad03153eb37010a`

The bridge's read-only rollback-list action returned an empty list (`R\t-\t-\t-\n`), so there was no eligible applied sync to preview or restore. No shortcut sync or rollback was applied. The main management-center process was already running before installation and was left untouched; a separate review instance used the installed binary.

## Verification

- GTK UI contract and desktop bridge tests: 48 passed.
- Full Native Termux suite: 868 passed, 1 skipped (122.933 seconds). The runner printed its existing post-suite GUI-monitor diagnostic (`Native Termux required`) after the successful test summary.
- Native `clang -O2 -Wall -Wextra` build and `--self-check`: passed (GTK 4.24.1, VTE 0.84.1).
- `git diff --check`: passed.
- Installed identity hashes: source C, bridge, binary, launcher, and desktop entry all matched.

## Limits and next work

The GTK control's actual button activation and resulting chooser/preview/confirmation flow remain **UNVERIFIED**. The agent did not inject UI input; human-operated visual interaction is required for that acceptance. The full suite and static GTK contract tests do not substitute for this. The shared GUI control, CLI, TUI, Web rollback flow, and cross-process mutation locking still need the broader P4 audit and parity work described in [shortcut rollback evidence](2026-10-22-p4-shortcut-sync-rollback.md).
