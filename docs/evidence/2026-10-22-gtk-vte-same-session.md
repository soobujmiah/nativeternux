# GTK/VTE same-session terminal handoff — 2026-10-22

Phase: P4; same-session terminal acceptance passes for CLI, authenticated Web API, TUI, and installed GTK/VTE on the isolated replay guest.

## Live Native run

Command:

`DISPLAY=:1 "$HOME/.cache/ternuxx-ui-check-venv/bin/python" tools/check_terminal_handoff.py --alias ternuxx-replay-p4 --gtk-display :1 --gtk-screenshot docs/evidence/2026-10-22-gtk-vte-same-session.png`

Result: **PASS**, exit 0.

One CLI-started session, `proot-bbed88095bd149bfb5aad1d8da33b92d`, was detached and attached in order through the authenticated Web terminal API, TUI, then the installed GTK/VTE client. Every client exchanged its own marker and exercised terminal sizing. The VTE screenshot visibly contains `GTK_VTE_HANDOFF_b070987d1a115e78` and guest-reported geometry `40 84`. Screenshot SHA-256: `f9e7edd3c39fcc0d144756bec80e4c3b9fbffd3808a4d64db457358416941bb1`.

GTK detached using Ctrl-]. The same verified session remained available, then the checker stopped the exact session through broker preview/confirmation and recorded it stopped/released. The private broker state was removed. The replay alias receipt and root identity were checked; default Debian root device/inode and protected profile hash were unchanged. The pre-existing Codex PRoot process was not signaled. The owner's separate Management Center remained open on :1 through a second repeat run after test-window cleanup was scoped to a dedicated test title.

Installed/source parity after that repeat run:

- GTK C source SHA-256: `433dbc8012265cb172b8d4e2f2ebaeaebca746aa987af88f763e8552fbd1d3056`
- Installed GTK binary SHA-256: `4451a45679a0fd50ba04e84b0fb8c9360d848338a01281d6080b79f64604eeab`
- The installed identity record reports the same source and binary hashes.

After the GTK test-instance cleanup change, the full Native regression command `bash scripts/repo_test.sh` passed **847/847** in 99.597 seconds (exit 0). The focused GTK UI contract suite passed 5/5.

The GTK test attach mode accepts only the exact managed session-ID format and runs under a separate GTK application ID. The checker preflights its Python PTY dependency, display socket, installed launcher, and X11 tools before creating a broker. An initial preflight attempt used the system Python without the existing `pyte` checker dependency; it started no guest session. Its exact empty private broker was stopped and removed before the successful venv runs.

## Scope limit

This proves the same running replay session can be handed across all four clients with GTK/VTE I/O, resize, detach, and exact cleanup. It does not close the remaining P4 provider/configuration gates, the GTK replay-guest apply flow, browser-rendered Web controls, graphics workload qualification, fresh rollback, or the overall repository audit.
