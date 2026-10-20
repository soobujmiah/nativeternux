# PRoot GUI on the native Termux display

**Owner direction:** 2026-10-19 (Asia/Dhaka)
**Execution:** native Termux checkout over SSH port 8022, based at `69e378eb33247678437bda4b2de9ab25f6bcb91d`

## Required experience

Use the native Termux:X11/XFCE desktop on `:1` as the one GUI session. Specific Debian GUI applications should open as windows on that desktop through shared-management app operations. A full Debian XFCE desktop must appear inside a nested window hosted by `:1`; it must not start another Termux:X11 Activity or separate PRoot `:0` desktop.

The current Debian PRoot must be adapted in place. Reinstalling/replacing/pruning the guest or invoking the owner-customized `~/x.sh` is out of scope.

## Read-only findings

- `ternuxx status --json` reported `status=degraded`, `display=:1`, `supervisor=no`, `x11=no`, and `xfce4_session=no`; the managed native `:1` session was not running at check time.
- `ternuxx proot status --json` found installed Debian and did not enter the guest.
- A read-only guest PATH check found `/usr/bin/startxfce4` and `/usr/bin/xfce4-session`; `Xephyr` and `Xnest` were absent.
- The existing specific-app shared-X11 path is already catalog-backed and targets the active native display. It can be exercised after `:1` is healthy.

## Implementation in this pass

- Disabled new starts through the legacy separate-display `scripts/proot-gui0.sh`; retained its status and ownership-checked stop handling for any old session.
- Kept canonical `ternuxx proot gui` routed through the Ternuxx-owned script; help now states that start is unavailable until the nested shared-display adapter exists.
- Updated P4 roadmap requirements to mandate native `:1`, nested full XFCE, previewed additive dependencies, and no reinstall or destructive guest changes.

## Verification and remaining work

- Regression test confirms a `:0` start fails closed without creating session state.
- Focused launch/routing tests: **7/7 passed**.
- Full native Termux suite: **333/333 passed in 76.890 seconds**.
- `bash -n scripts/proot-gui0.sh`, `git diff --check`, and repository metadata validation passed.
- No native GUI lifecycle, PRoot launch/stop, package operation, guest file write, or rootfs mutation occurred.

Full XFCE within `:1` is **not yet implemented or runtime-qualified**. It requires a nested X server dependency (absent in the current guest) plus a P4 ownership-aware lifecycle adapter. This work remains behind P3 per the phase order. No package was installed.
