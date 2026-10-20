# Native X11 activity request and fallback regression evidence — 2026-10-19

## Change

P3 requires a native desktop start to request the Termux:X11 Android activity and clearly report manual-open fallback while keeping GUI visibility separate. The implementation already sent the fixed `com.termux.x11/com.termux.x11.MainActivity` component through `$PREFIX/bin/am`; fixture coverage now exercises its accepted, rejected, and unavailable outcomes without contacting Android.

- Accepted result: confirms the exact `am start --user 0 -n ...` arguments and states GUI visibility remains unknown.
- Rejected result: returns an unsuccessful activity-request outcome and tells the user to open Termux:X11 manually.
- Missing launcher: returns an unsuccessful outcome and the same manual-open guidance without invoking a command.

These checks do not establish Android background policy, actual activity visibility, or boot delivery.

## Verification

- Focused Native Termux desktop-lifecycle fixture tests: 16/16 passed.
- Full Native Termux repository suite via SSH 8022: 350/350 passed in 71.566 seconds.
- `git diff --check`, phase-state JSON validation, and generated phase-document refresh passed.
- No Android activity was launched. No device service, desktop, boot profile, Termux setting, or Debian PRoot state changed.

P3 remains in progress; cold-boot and Android background-policy qualification remain open.
