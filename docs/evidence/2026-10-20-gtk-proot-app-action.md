# Native GTK named PRoot app action — 2026-10-20

Phase: `P3` (incremental; no phase gate marked complete)

## Change

The Native GTK management center now exposes a resource-specific launch control
for `proot.debian.workloads`. It accepts only the named app IDs in the existing
PRoot app catalog, explains that launch uses the existing guest and current
Native display, and dispatches through the shared `proot.app.launch` operation
using the typed local bridge. It does not install packages or change guest
configuration. The Web client remains unable to launch PRoot apps because
`applications.launch` is not granted to its deliberately narrow HTTP session.

## Verification

- Bridge tests verify a known app routes to `proot.app.launch` and an arbitrary
  string is rejected before dispatch.
- `clang -O2 -Wall -Wextra -Werror -fsyntax-only ...` verifies GTK source syntax.
- Full Native repo suite passed: 588/588 tests.
- GTK binary installed through `./tx mng center install`; SHA-256:
  `077293ba04f7428c99298d42d67325e54e5b5dab5acd795ebc878a9bcf1aeffd`. The
  running management window was not restarted.

The new GTK control was not clicked or visually reviewed. Its source and typed
bridge are verified, but end-to-end UI launch remains unqualified. Existing
PRoot menu/window evidence remains distinct; this does not claim all guest apps
are installed, launchable, or accelerated.
