# P4 dynamic Debian application discovery — 2026-10-23

## Scope

The managed PRoot shortcut inventory now reads visible Debian desktop entries from the configured guest rootfs, localizes names/comments, checks executable availability, reports shortcut ownership/state, and omits unavailable applications from bulk shortcut creation. Web and TUI launch flows can select discovered desktop entries by friendly name without asking users to type a desktop ID. GTK launch and shortcut forms use friendly selectors for the fixed catalog; the complete dynamic GTK wizard remains open.

## Live device observation

Read-only `proot.shortcuts.list` on Native Termux returned 35 available Debian desktop applications and 7 diagnostics. No guest files were changed by discovery. The owner’s active PRoot was not used as a disposable test target.

## Verification

- `python3 -m unittest tests.test_terminal_ui tests.test_proot_shortcuts tests.test_management_http_runtime tests.test_management_center_ui_contract -q`: 103 tests passed, 1 skipped.
- `bash scripts/repo_test.sh`: 875 tests passed, 1 skipped (128.170 seconds).
- `git diff --check`: passed.
- `bash scripts/install-management-center.sh`: succeeded on Native Termux.
- Installed GTK binary source identity matches `apps/management-center/management-center.c` and `scripts/management_desktop_bridge.py`; installed binary hash matches the installer identity record. Launcher and desktop entry hashes are recorded in `/data/data/com.termux/files/usr/libexec/ternuxx/management-center.identity`.

## Limitations

No GTK interaction was injected. The menu entry and latest binary were installed, but actual human-operated GTK interaction remains unverified. This evidence does not qualify broken-rootfs recovery, cold boot, rootfs migration, complete client parity, or P4 exit.
