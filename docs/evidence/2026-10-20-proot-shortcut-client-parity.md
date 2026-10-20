# P3 — PRoot shortcut management in shared clients — 2026-10-20

Phase: `P3`

## Scope

Added catalog-backed add/remove controls to the Native TUI, authenticated Web Console, and GTK Management Center. Each client calls the existing proot.shortcuts.preview and proot.shortcuts.apply service operations. Shortcut listing and broad proot.shortcuts.sync remain separate.

## Safety and authorization

- TUI and GTK show the exact affected path and before/after state, then require explicit confirmation.
- Web requires the narrow applications.shortcuts.manage scope, CSRF, durable idempotency, preview, and browser confirmation tied to the returned plan ID.
- This Web scope does not grant applications.manage; broad shortcut synchronization is denied.
- The shared apply operation re-previews the target and rejects stale plan IDs. The shortcut manager preserves non-Ternuxx or conflicting entries.
- No live menu entry was added or removed during source verification.

## Evidence

The full Native Termux repository suite passed (592 tests). Focused checks covered TUI preview/cancel/apply behavior, GTK bridge arguments, exact capability isolation, and Web mutation authorization. GTK C compiled with -Wall -Wextra -Werror; the installed binary passed --self-check (GTK 4.24.1). Installed artifact SHA-256 is db51aa5e5ceda15d94fae92ecac8584936f3bc62d589e479ad68bb36428edf2f and matches management-center.identity. Read-only tx status still reported the existing Native :1 session running. Visual interaction was not performed and the running GTK window was not restarted.

## Limitations

Actual menu rendering and click behavior remain pending owner visual qualification. Debian app availability is checked by the existing preview logic, but this increment did not modify the guest, relaunch applications, restart the desktop, or change the current PRoot Apps menu.
