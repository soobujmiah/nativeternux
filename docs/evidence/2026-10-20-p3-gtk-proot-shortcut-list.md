# P3 GTK PRoot shortcut inventory action — 2026-10-20

Phase: `P3`

## Change
Added a GTK Management Center action on the PRoot workloads resource to list the shared PRoot shortcut inventory. It calls typed `proot.shortcuts.list` through `management_desktop_bridge.py`; it is read-only and shows app IDs, shortcut ownership/state, and unverified guest availability. Existing named-app launch and one-shortcut preview/confirm/apply flows are unchanged.

Updated the capability matrix and CLI help to include the GTK inventory action and correct the Web scope description: Web already has previewed single-shortcut changes, while Cron job mutation remains unavailable there.

## Evidence
- `python3 -m unittest tests.test_management_desktop_bridge -q`: 19 passed.
- `clang -O2 -Wall -Wextra -fsyntax-only apps/management-center/management-center.c $(pkg-config --cflags gtk4)`: passed with Native GTK4 headers.
- `bash tests/test_cli_help.sh`: passed.
- Ran `./tx mng center install`. The installer verified the previous identity, rebuilt and installed the GTK binary, and recorded matching source/bridge hashes. Installed binary hash: `d39ec3223a3b59551e9b20fca36c911b81d17b973fb945a77a23ce8d2be4e429`. `--self-check` reports GTK 4.24.1.
- Invoked the installed checkout bridge read-only: `python3 scripts/management_desktop_bridge.py shortcut-list`. Shared service returned 14 catalog entries successfully; all showed shortcut state `absent` and application availability `unknown` at observation time. No guest application availability is inferred.
- Did not open/restart the GTK window or restart Native XFCE. The new button's visual placement remains unreviewed.

## Remaining P3 parity work
GTK now lists shortcuts, launches named PRoot apps, and supports exact single-shortcut changes. TUI/Web/GTK still do not share all CLI operations. Cron job create/update/remove currently lack a common preview/explicit-confirm/apply contract and client actions. Boot, backup/restore, recovery-write, PRoot session lifecycle, and SSH deploy limitations also remain in the current capability matrix.
