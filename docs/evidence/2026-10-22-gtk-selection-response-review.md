# GTK selection and asynchronous result review — 2026-10-22

Phase: P4; this is a focused usability remediation, not a phase exit.

## Finding

A live Native screenshot showed the replay-guest resource selected while the details pane still contained a previous Debian status report. GTK inspections are asynchronous, and an older inspection could finish after the user selected a different resource, making the visible result appear to belong to the new selection.

## Change and verification

The GTK request callback now discards an inspect response when its resource ID no longer matches the selected resource. Other operation results and their shared-service effects are unchanged.

The installed Management Center was rebuilt on Native Termux and its exact source C and binary hashes match the installed identity record:

- Source: apps/management-center/management-center.c SHA-256 e9b081f6f0de908172b8d4e2f2ebaeaebca746aa987af88f763e8552fbdc7a8d
- Installed binary: $PREFIX/libexec/ternuxx/management-center SHA-256 7f6677a123890964fc4558194dbd821dde4c2e2cf1b4d196bd79a73e839cc144

The focused UI source-contract suite passed 4/4. A live Native X11 smoke review on display :1 (720×980 app window) switched between the PRoot and System & health categories after deployment; the final view remained on the selected System & health resource and its current health report. No guest action or desktop lifecycle operation was run.

## Limits

The focused test asserts that the stale-response guard is present; it does not deterministically delay a Native GTK subprocess callback. The live selection review is a smoke check, not a controlled race-injection test. Raw diagnostic reports still expose technical fields in the details pane and need a separate progressive-disclosure/readability pass. GTK/VTE same-session handoff, browser-rendered controls, and remaining P4 gates stay open.
