# GTK management-center live visual review - 2026-10-22

## Target and conditions

- Native Termux checkout: `$HOME/ternuxx`, branch `main`.
- Native X11 display: `:1`, 752 x 1124.
- Application: the visible `Ternuxx Management Center` GTK window, PID 17842, executable `$PREFIX/libexec/ternuxx/management-center`.
- PRoot, SSH 8022/8023 and XFCE session were not stopped or changed.

## Finding A35

The recovery history view rendered internal operation IDs, ISO timestamps and long rollback references in the main detail pane. It could overflow the small portrait window. The action area was placed after the detail area, so its position depended on the selected resource's output. An empty action area reserved a large blank block.

- Severity: P2 usability/privacy.
- Source: `lib/management_presentation.py::format_activity_history`, called by `scripts/management_desktop_bridge.py::history`; pane ordering and visibility in `apps/management-center/management-center.c::show_resource` and `active`.
- Root cause: GTK used the generic recursive report formatter for journal records; the UI always allocated the action scroller even when all its buttons were hidden.
- Fix: show the latest eight journal entries with friendly operation/state labels, local readable timestamps, bounded detail text, and opaque journal/rollback references redacted. Place available actions before the independently scrolling details and hide the action scroller when no action is available. Reduce the category/list pane minimums for portrait-sized screens.
- Regression: `tests.test_management_desktop_bridge.ManagementDesktopBridgeTests.test_history_bridge_hides_internal_ids_and_formats_timestamps` plus the focused bridge suite, 28 tests, passed.
- Live source/install check: installer identity reports the current C and Python bridge SHA-256 values; visible process PID 17842 resolves to the installed executable. The operation-history view was opened on the Native X11 window and visually inspected after install. It showed 52 records, latest eight, readable dates and no opaque IDs. No management mutation was applied.
- Status: PASS for this finding's defined history and layout behavior. The broader GTK action parity and all-client UX audit remain open.

## Installed artifact identity

- C source: `87c80b74ca66b4c1d20c5796c4ded9cc89f828355c96fb48aefc33e5c2da7548`
- Python desktop bridge: `f2c5bbd4df2d9b2f4637f18f1f8e0a0d404e48f37aa430a2d860f56717624e6d`
- Shared presentation module: `01921ee54079bcaec8eb565bcde0531a9ebdf64b8663db83e9c4e91af2be7b7a`
- Installed GTK binary: `85ce1b5f042d1e531cba113126faa8b28189de12c2bf98bd50b21ea139b6b493`

This live review does not prove client parity, future boot behavior, or the rest of the repository's acceptance matrix.
