# Web named PRoot app action — 2026-10-20

Phase: `P3` (incremental; no phase gate marked complete)

## Scope

Added one narrow Web mutation: `applications.launch` authorizes only the
existing `proot.app.launch` operation with an app ID from the fixed catalog.
The browser first loads the shared read-only shortcut/app catalog, displays each
named entry and shortcut state, then requires an explicit per-app confirmation
before dispatch, with the target X11 display explicitly chosen or inherited from the Web service environment. Requests use the existing CSRF proof and durable idempotency
key. App availability in the Debian guest remains unknown until launch; this
does not enable PRoot session start/stop, arbitrary desktop IDs, command strings,
shortcut edits, arbitrary desktop-entry IDs, or guest configuration changes. Ordinary management HTTP mode
stays read-only.

## Verification

- HTTP runtime tests (12/12) confirm Web scope includes catalog app launch,
  rejects arbitrary desktop-entry IDs, and still denies PRoot session lifecycle;
  CSRF, idempotency and the other existing scope checks remain covered.
- Web UI source checks verify the named-app catalog flow, display validation,
  per-app confirmation and mutation request path.
- Full Native repo suite passed: 588/588 tests. GTK source compiles with
  `clang -O2 -Wall -Wextra -Werror -fsyntax-only ...`; repo-knowledge verify
  reports 0 findings.
- The browser was not opened and no PRoot application was launched from Web;
  mobile/visual review remains pending owner-operated acceptance.

## Remaining scope

See the [capability matrix](../architecture/CAPABILITY-MATRIX.md) for the
complete per-client boundary. Cron mutation, timezone mutation, PRoot session
lifecycle, shortcut edits, boot, backup/restore, deployment/rollback, and service
log/progress controls remain outside the Web session.
