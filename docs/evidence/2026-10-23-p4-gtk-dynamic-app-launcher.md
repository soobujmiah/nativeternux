# P4 GTK dynamic Debian app launcher — 2026-10-23

Phase: `P4`

## Change

The GTK app launch flow now obtains its app list from `proot.shortcuts.list` through the typed local management bridge. It displays friendly names for the fixed Ternuxx catalog and dynamically discovered visible Debian desktop applications. Internal catalog/desktop IDs stay behind the GUI selector and are revalidated by the shared service at launch.

The bridge returns 35 live available Debian desktop entries on this device. This is inventory evidence only; no app was launched and no guest file or configuration was changed during discovery.

## Evidence

## Evidence

## Verification

- `clang -O2 -Wall -Wextra ... management-center.c`: passed with no warnings.
- `python3 -m unittest tests.test_management_center_ui_contract tests.test_management_desktop_bridge -q`: 53 passed.
- `bash scripts/repo_test.sh`: 878 passed, 1 skipped in 129.529 seconds.
- `management-center --self-check`: passed (GTK 4.24.1, VTE 0.84.1).
- `scripts/management_desktop_bridge.py proot-app-options`: returned 35 dynamic entries.
- `scripts/install-management-center.sh`: installed successfully. Installed source C, bridge, and binary hashes match `management-center.identity`.

## Limits

This delivers dynamic launch selection, not per-app dynamic shortcut CRUD in GTK. GTK shortcut add/remove still targets the fixed catalog; bulk sync/rollback remains available separately. No UI automation or user click was performed. Actual launch rendering, human interaction, rootfs migration, broken-rootfs recovery, cold boot, and P4 exit remain unverified/open.
