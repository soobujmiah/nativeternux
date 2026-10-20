# P3 PRoot session client-parity audit — 2026-10-21

Phase: `P3`

Status: this pre-implementation audit snapshot is superseded for TUI/Web/GTK session availability by [the follow-up implementation and Native live check](2026-10-21-p3-session-client-implementation.md). The bounded isolated-probe controls are now present in all four clients. The remaining parity question is the foreground `debian-interactive` login, which requires an attached TTY and remains CLI-only; no owner-accepted exception is recorded, so P3 parity acceptance remains open.

## Evidence

Read the current `docs/ROADMAP.md` P3 deliverables/exit gate, `docs/architecture/CAPABILITY-MATRIX.md`, the 2026-10-20 management client-parity report, and the Native source for `lib/terminal_ui.py`, `lib/management_http_runtime.py`, `lib/management_http_adapter.py`, `lib/management_web_ui.html`, and `apps/management-center/management-center.c`.

At the time of this snapshot, the source and matrix showed this split; the following client-availability findings were subsequently superseded by the implementation evidence linked above:

- CLI exposes typed PRoot session listing, preview/start, exact-owned preview/stop, health, and recovery operations through the shared service.
- TUI, Web, and GTK expose selected named-app launch and shortcut actions, but do not expose PRoot session lifecycle or recovery actions.
- The Web capability allowlist intentionally excludes `proot.session.manage` and its mutation set excludes `proot.start`/`proot.stop`.
- The `debian-interactive` profile requires an attached foreground TTY; current source has no detach/reconnect or browser PTY broker. Three recent live attempts failed closed at guest cwd/numeric UID verification before a shell was exposed.
- The fixed `isolated-probe` profile is a bounded headless process with preview/apply and exact-owned stop APIs already present in the shared service. Exposing only this fixed profile to non-CLI clients is a possible parity slice; it does not make the interactive shell a Web action.

The project’s P3 exit gate requires supported session controls to use the shared service across CLI, TUI, Web, and GTK, or have a documented owner-accepted limitation. The matrix records the gaps, but no owner-accepted exception for missing session controls was found. At that snapshot this gate was **open**. The later fixed-probe controls close the inventory/recovery and bounded start/stop gap, while the CLI-only interactive TTY profile still needs an owner-accepted client boundary or a supported attached-terminal route. Earlier owner visual acceptance of the clients does not accept missing session lifecycle actions.

## Next implementation at audit time (superseded)

The next-step text below records the plan that led to the follow-up implementation; it is retained as history, not as the current next implementation. Design the common session view and exact-preview actions before changing client capabilities. Add read-only session state/recovery detail and a bounded `isolated-probe` start/stop flow through the existing typed service to TUI, Web, and GTK, with capability/CSRF/idempotency tests and a UI-visible explanation that it creates only a fixed short-lived probe. Do not expose arbitrary commands or let Web start `debian-interactive` without an attached-terminal design. Keep interactive login live qualification separate: the latest exact identity check still fails closed, so do not retry it or signal any existing PRoot process as part of this client work.

This is a source audit, not an implementation or live client test. P3 remains active; P4 must not be treated as accepted while this and the other P3 exit gates remain open.
