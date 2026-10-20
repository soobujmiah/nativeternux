# P3 PRoot session client implementation and GTK live check - 2026-10-21

Phase: `P3`

## Evidence

## Shared client implementation

The shared typed service backs PRoot session management in CLI, TUI, Web, and GTK. TUI, Web, and GTK can list sessions, inspect per-session recovery, preview and apply only the fixed `isolated-probe` profile (300 seconds), and stop only after a fresh preview verifies Ternuxx ownership and binds the exact session ID to the plan. TUI and GTK require a visible explicit confirmation. Web additionally requires authenticated scope, CSRF, idempotency, and explicit browser confirmation; its HTTP adapter restricts starts to the fixed probe and blocks recovery reconciliation.

The desktop bridge validates session IDs and full plan IDs before dispatch. TUI/Web/bridge tests cover plan binding, fixed profile, refusals, request guards, and exact stop dispatch.

## GTK layout and Native live interaction

The first Native screenshot showed that the original three-pane layout requested more width than the 752-pixel screen and hid the resource and detail panes. The GTK client was adjusted to a 720x900 default, explicit pane positions, wrapped category/resource labels, stacked action buttons, dark detail-view styling, and inline preview/confirm/cancel controls. Inline confirmation replaced an alert that rendered blank in this GTK session.

The updated client was installed by `bash scripts/install-management-center.sh` after the installer verified the previous binary/launcher identity. Installed binary SHA-256: `02331a8900c07ac9382844cd0f0a3e0fbf50eef4521b03b385738dff83c16605`. The installed identity records source C SHA-256 `73b71729898b91e7f2345e4dc8df61037e665f37783f2cd4e6fbd383622b1366` and bridge SHA-256 `60349c473fbe8309f5ec82e762ef7d31ed69d31de279bac215b7b507f17a35ac`.

On Native Termux, `tx status --json` verified the existing desktop running on `:1`; the Management Center opened as a 720x900 window on the 752x1049 screen. I visually checked the wrapped category labels, the selected Debian PRoot resource, and its action buttons. In GTK, session inventory returned nine existing records, all stopped/released. Recovery inspection of one stopped record reported `process_absent` and released ownership. The fixed probe preview showed its 300-second bounded impact; I selected Cancel. A following read-only inventory still showed exactly nine stopped sessions. No probe was started, no session was stopped, and no existing Debian process was signaled. I closed only the Management Center test process I opened; the Native `:1` desktop, SSH 8022, and managed SSH 8023 remained up. Temporary screenshot files were deleted after inspection.

## Current Native P3 read-only snapshot

- Native desktop: running on `:1`; session stack remains live.
- Existing Debian: installed; Ternuxx guest ownership remains `unverified`; no guest entry occurred.
- Ternuxx PRoot registry: nine records, all `stopped` with ownership `released`.
- Doctor: warning for the separate development SSH 8022 wildcard/password policy; no policy change was made.
- Boot helpers `00-ternuxx-services` and `ternuxx-recovery`: installed identity matches source; both mode `0700`.
- Termux:Boot Cron script: identity matches; companion and receiver enabled; scheduler running. Actual device boot delivery is `not_yet_verified`.
- Managed SSH 8023: Runit definition and process identity verified; loopback banner responds. TCP listener-to-port mapping remains `unknown` because Native `/proc/net/tcp*` access is denied. No SSH policy changed.

## Verification

- Focused Native client suite: `python3 -m unittest tests.test_terminal_ui tests.test_management_http_runtime tests.test_management_http_adapter tests.test_management_desktop_bridge tests.test_management_authorization -q` - 81 passed.
- Full Native Termux suite: `bash scripts/repo_test.sh` - 646 passed in 104.565 seconds.
- GTK compile: `clang -O2 -Wall -Wextra -fsyntax-only apps/management-center/management-center.c $(pkg-config --cflags gtk4)` - passed after layout and confirmation changes.
- `git diff --check` and `python3 -m tools.repo_knowledge verify` - passed; latest knowledge verification returned 0 findings.

## Remaining P3 gates

GTK session controls are source-, compile-, install-, and live-UI-checked. Managed SSH listener attribution and Android cold-boot delivery remain unverified. Cold-boot delivery is not inferred from a manual script run. P3 stays active; P4-P10 must remain planned until P3 passes.


## Follow-up: unprivileged listener attribution probe

A read-only attempt to use Android NETLINK_SOCK_DIAG for TCP listener enumeration was denied at socket creation with PermissionError: [Errno 13]. No listener rows or inode mappings were obtained. lsof exposed no 8022/8023 listener rows, and the existing /proc/net/tcp* path remains denied. No package was installed, no privilege was requested, and no SSH process or configuration was changed. Listener ownership remains unknown.


## Capability-matrix reconciliation

A current-state matrix audit found stale per-operation and independent-runtime rows that still marked TUI, Web, and GTK PRoot session controls unavailable. Updated those rows, including named-app launch availability, to match the shared typed service and the implemented client surfaces. The documented limits remain explicit: non-CLI clients may only start the fixed bounded probe; Web mutations require scoped authentication, CSRF, idempotency, and confirmation; recovery reconciliation remains CLI-only; live interactive TTY identity qualification is still open.
