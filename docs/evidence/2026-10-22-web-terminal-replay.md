# Native Web terminal replay — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

The actual authenticated Web page was run in Firefox ESR from the separately installed `ternuxx-replay-p4` guest. Native Termux hosted a private loopback Web server and a private production terminal broker pointed only at that replay guest. The browser used an isolated profile; Marionette sent real key actions to the terminal. A unique guest marker returned through the browser output polling path. After the browser window changed size, a second command returned the same row/column size as the accepted Web resize request. The browser detached, reattached the verified owned session, returned another guest marker, then previewed and confirmed exact graceful close. The broker disconnected and its sole test session stopped. [Machine-readable result](2026-10-22-web-terminal-live.json).

## Failure and correction

The first full browser replay created an exact owned guest session but failed after attaching: terminal resize returned `terminal_channel_rejected`. Request tracing showed preview, start and attach returned HTTP 200, then resize returned HTTP 403. The broker generation is a random 63-bit integer; JavaScript JSON numbers can round it before sending it back. The HTTP adapter now gives the browser a canonical decimal generation string, parses only a bounded canonical string on subsequent requests, and passes the exact integer to the broker. A focused regression uses a generation above JavaScript's safe-integer limit and rejects numeric, malformed and mismatched values.

The Web confirmation now shows the selected guest alias/rootfs, and exact close shows SIGHUP, readable scope and impact. The session picker and status use a short identifying suffix instead of a full opaque ID. Failed replay sessions were stopped through their own verified stop plans; their exact private brokers and scratch profiles were removed. No default broker, working guest, SSH channel or desktop process was restarted.

## Evidence

The final private browser replay passed start, I/O, observed resize, detach, reattach, exact close and scoped working Debian root/profile preservation. A 940-pixel headless Firefox screenshot was inspected: the terminal renderer, shell prompt, returned markers and 20 × 101 guest size were visible; the dialog fit the viewport. The task-owned temporary screenshot was inspected and deleted; it was not committed to product or repository data. This one screenshot does not establish all viewport layouts or performance.

The affected HTTP adapter tests passed 15/15 after the wire fix. The full Native suite passed 750/750 in 110.682 seconds. [Source-bound result](2026-10-22-web-source-regression.json). The opt-in checker is `tools/check_web_terminal.py`; it retains private state on failure for exact ownership-checked recovery, and removes it after a passing run. Browser sessions and terminal bytes are not committed.

GTK/VTE terminal lifecycle, cross-client handoff, broader native/guest parity, fresh rollback and graphics workload qualification remain open. Existing live Web processes were not found during this replay; the current source was exercised through a newly started private Native Web runtime.
