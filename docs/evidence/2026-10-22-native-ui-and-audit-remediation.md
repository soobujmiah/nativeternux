# Native UI implementation and repository audit remediation — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Implementation

Work ran in the Native Termux checkout through SSH 8022. The full repository objective remains active in [the audit worklist](../audit/REPOSITORY-AUDIT.md).

The approved stable-action Web design is implemented using real resource controls. Actions precede independently scrolling inspection/results; mobile/tablet quick actions invoke the selected resource. Numbered categories use the shared catalog purpose order in Web, TUI and GTK. Repetitive availability metrics were replaced by a concise count. Availability is distinguished from live state. The explicit hidden rule protects app/policy/action sections before login. A late asynchronous response cannot be displayed as another resource's status.

Interactive numbered/typed Auto browser selection now resolves to a real launch target. Browser and clipboard failure stops without revealing the code by default; explicit terminal fallback also works when browser launch fails. Web mode is supplied in a copied runtime environment instead of leaking into the caller's environment; the read-only command explicitly overrides an inherited Web-mode flag.

A literal escape at the end of the terminal service test module was repaired. The Android clipboard-failure fixture now chooses Android explicitly. The baseline suite had one import error and one failure; those were not treated as successful tests.

The guest GUI helper no longer requests the Android Activity when the Native X11 server is already verified. It preserves the desktop/session lifecycle.

## Evidence

- Full Native unit/fixture suite: 703/703 passed in 99.223 seconds after the runtime/category/layout/helper and response-binding fixes, including the read-only environment-scope regression.
- Focused catalog/TUI/GTK bridge/HTTP runtime/service deployment checks: 87/87 passed before final browser refinements.
- [Machine-readable browser result](2026-10-22-web-ui-browser-check.json) records actual checks and source fingerprints. Headless Firefox ESR 153.4.0 verifies exact 390/752/1440 CSS-pixel widths, no page overflow, stable actions under long details, login/hidden state, category/search, the 8022 lifecycle boundary, Wake Lock status, and terminal renderer/dialog. The checker uses an isolated profile/test state and allows only catalog/session-inventory server reads; delayed-response behavior uses a browser-local synthetic response.
- Actual Native tx web --browser proot smoke run opened a temporary loopback listener and an isolated Firefox window. An X11 capture confirmed the masked one-time code in the login field and no unauthenticated app controls. The test listener and its exact browser window were closed afterward; existing browsers were preserved.
- A visible Firefox run on the existing Native X11 display passed with actual content viewport 742×881 for a 752px requested outer window. This is separate from exact headless viewport qualification.
- GTK4/VTE rebuilt successfully. Installed source C, desktop bridge and binary hashes all match the identity record. Existing running app processes were not stopped.
- Installed canonical recovery modules match source; their installed-path import closure succeeds. The installed tx shim dispatches to the current checkout.
- [Selected deployment comparison](2026-10-22-native-selected-deployment-parity.json): tx shim, both boot helpers, SSH/broker Runit definitions and recovery modules match source. The GUI monitor service is not installed; that is an open source/live gap. Native desktop remains running and Doctor reports managed 8023 identity/config/banner passing with socket correlation unknown.
- Source/installed parity is partial; uninspected targets remain open. No clean-install or full managed guest attach is claimed.

## Documentation reconciliation

Current handoff, architecture, client matrix and testing guidance now link their authoritative sources. Old handoff and matrix snapshots were archived with local links adjusted. Manifest phase status points to canonical phase state instead of repeating an obsolete phase. README no longer repeats contradictory graphics/phase claims. The SKB pointer was corrected after GitHub API reported public visibility. Accidental repeated asset hashes/test bullets and a trailing literal escape were removed from the earlier broker evidence.

The document inventory is a coverage mechanism, not proof that every file has been read. Full review of all narrative/structured evidence, ADR implementation claims, live components and reproducibility remains open.

## Preservation

No reboot, Native desktop/service stop, working PRoot signal, rootfs replacement, package cleanup, SSH credential/policy change, or shared-storage access occurred. Firefox used disposable shared-tmp profiles and was closed by its own automation session. Only temporary test/browser state was removed. GUI screenshots and test logs are temporary and are removed after inspection; machine-readable scoped evidence is retained here.
