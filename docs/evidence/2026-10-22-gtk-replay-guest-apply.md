# GTK replay-guest apply/restore — 2026-10-22

Phase: P4. Gate: PASS for the installed GTK client’s exact-preview retirement and restore cycle on the isolated ternuxx-replay-p4 test guest.

## Native GUI run

The Management Center was opened on the already-running Native X11 :1 desktop. The dedicated “Ternuxx replay guests” resource exposed its replay-only lifecycle action. The original GTK4 alert confirmation painted as a blank surface on this device, so I replaced that action’s confirmation with an inline, target-specific review panel in the existing action pane. The review showed the exact alias, operation impact, no-delete guarantee, and explicit Cancel / Retire or Restore buttons. Cancel remains available, and the apply button has no default keyboard activation.

The live GUI sequence passed:

1. Previewed retirement for ternuxx-replay-p4; the visible confirmation named the exact alias and described the reversible same-directory move.
2. Applied from the GTK action. The shared service returned retired, backup ID cbd1c2b9577241969a12c073378a6417, container inode 101280, and files_deleted: false.
3. Selected restore, entered the exact alias and returned backup ID, previewed the restore, reviewed the visible target/effect, and applied from GTK.
4. The shared service returned restored and files_deleted: false. Read-only post-check confirmed container device/inode 65086:101280 and rootfs inode 5078478; a fresh exact retire preview again identified the installed test guest.

No Debian-rootfs operation was requested. Post-check observed the default Debian rootfs at device/inode 65086:3240111, its selected generated profile SHA-256 738f055d173b2e283c6192d9031857002ddfe16952090d7345f343ec8b5f3c22, and the previously unverified host PRoot PID still alive. The guest-management operations target only the receipt-verified replay alias; they do not signal that unrelated process. The Management Center remains open on :1.

## Source, install, and checks

- Native source: apps/management-center/management-center.c
- Native regression: python3 -m unittest tests.test_management_center_ui_contract -v — 6/6 passed.
- scripts/install-management-center.sh rebuilt and atomically installed the GTK client.
- Installed identity reports C source SHA-256 edbd7ce14038d60ce6979352a2ec633a3134a12b2ec04028ed754d4ab020a918 and binary SHA-256 85d3dcc84b2646060fc793f6e7e987d842f438943c7b4733093a447518c28a91; both match the current source and installed binary.
- git diff --check passed.

## Scope limit

This closes the GTK replay-guest apply/restore gate for this exact replay alias and installed build. It does not qualify browser-rendered Web controls, all provider/configuration routes, clean-install rollback, the complete file-by-file audit, or overall release readiness. P4 remains open.
