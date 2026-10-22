# GTK replay-guest dialog review — 2026-10-22

Phase: P4
Gate: PASS for resource discovery, readable preview, confirmation content, and safe cancellation; GTK apply remains UNVERIFIED.

## Live Native review

Reviewed the installed Ternuxx Management Center on Native X11 display :1 at 752×1124; the app window is 720×980. Restarted only the management-center window after installation so it loaded the current Native checkout catalog. The fresh catalog listed “Ternuxx replay guests” as the third PRoot resource.

The first review exposed two UI defects:

- The single replay-guest action was inside the general action scroller and did not remain visible when the replay resource was selected. Moved it into a dedicated action row, kept the general action list independently scrollable, and verified the button is visible on the live screen.
- The dialog's explanation label expanded its window beyond the screen width. Wrapped it to 46 characters and set a 420×300 default dialog size; the copy now fits a 720-pixel display.

Clicked “Retire or restore replay guest…”, entered the exact replay alias, and requested a preview. The live shared service returned a plan for ternuxx-replay-p4; the GTK confirmation dialog showed the exact target, reversible move, no-file-deletion statement, and Cancel / Apply exact preview choices. Selected Cancel. The replay guest remained installed. No GTK apply was performed.

The confirmation-only screenshot is [2026-10-22-gtk-replay-guest-confirmation.png](2026-10-22-gtk-replay-guest-confirmation.png). Installed source, bridge, binary, launcher, and desktop-entry hashes were checked against the GTK identity record after rebuild and all matched. Three focused source-contract regression tests pass.

## Scope

This covers the installed GTK dialog's live discovery, preview, visible confirmation, and cancel path. It does not prove GTK apply/restore, restore backup selection UX, browser-rendered Web controls, or GTK/VTE terminal handoff. The real authenticated loopback HTTP API already passed the full retire/restore cycle separately. Existing Debian and the owner's active PRoot session were not changed.
