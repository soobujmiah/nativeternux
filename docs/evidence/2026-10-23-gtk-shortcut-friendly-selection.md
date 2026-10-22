# GTK PRoot shortcut selection form

Date: 2026-10-23
Runtime: Native Termux, installed Management Center

The GTK Manage PRoot shortcut form now offers friendly app names and Add/Remove dropdowns. It no longer asks users to type internal catalog IDs or action strings. Selection maps to the existing fixed allowlist and shared preview/apply service; it does not accept arbitrary commands.

Verification: 9 GTK UI contract tests passed; Native clang build and --self-check passed (GTK 4.24.1, VTE 0.84.1). The new installed identity record matched the current C source, bridge, binary, launcher and desktop entry. A new review instance displayed on Native X11 :1. The form's touch/selection/preview interaction remains unverified and requires human-operated input. Dynamic Debian desktop application discovery and per-app lifecycle are still missing from this selector; the existing bulk discovery/sync path is separate.
