# GTK replay-guest dialog review — 2026-10-22

Phase: P4
Gate: PASS for resource discovery, readable preview, visible confirmation, cancellation, and apply/restore on the installed GTK client.

## Live Native review

Reviewed the installed Ternuxx Management Center on Native X11 display :1 at 752×1124; the app window is 720×980. Restarted only the management-center window after installation so it loaded the current Native checkout catalog. The fresh catalog listed “Ternuxx replay guests” as the third PRoot resource.

The first review exposed two UI defects:

- The single replay-guest action was inside the general action scroller and did not remain visible when the replay resource was selected. Moved it into a dedicated action row, kept the general action list independently scrollable, and verified the button is visible on the live screen.
- The dialog's explanation label expanded its window beyond the screen width. Wrapped it to 46 characters and set a 420×300 default dialog size; the copy now fits a 720-pixel display.

Clicked “Retire or restore replay guest…”, entered the exact replay alias, and requested a preview. The live shared service returned a plan for ternuxx-replay-p4; the GTK confirmation dialog showed the exact target, reversible move, no-file-deletion statement, and Cancel / Apply exact preview choices. Selected Cancel. The replay guest remained installed. No GTK apply was performed.

The confirmation-only screenshot is [2026-10-22-gtk-replay-guest-confirmation.png](2026-10-22-gtk-replay-guest-confirmation.png). Installed source, bridge, binary, launcher, and desktop-entry hashes were checked against the GTK identity record after rebuild and all matched. Three focused source-contract regression tests pass.

## Scope

At the time of this initial review, GTK apply/restore and restore backup selection were unverified. The later GTK apply/restore run is recorded in [follow-up evidence](2026-10-22-gtk-replay-guest-apply.md). Browser-rendered Web controls remain open. GTK/VTE terminal handoff is separately recorded in [same-session evidence](2026-10-22-gtk-vte-same-session.md). Existing Debian and the owner's active PRoot session were not changed.

## Follow-up — live apply and restore

GTK4's standard alert surface rendered blank during the apply review on this device. Replaced only this replay-guest confirmation with an inline target/effect panel, defaulting keyboard activation to no mutation. The installed action now visibly shows the exact alias, no-delete guarantee, and explicit Cancel / Retire or Restore choices. Live GTK retirement and restoration both passed on the receipt-verified test alias; exact inodes were preserved. See [apply/restore evidence](2026-10-22-gtk-replay-guest-apply.md).
